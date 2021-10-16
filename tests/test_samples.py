import unittest
import mock
import os
import pandas as pd

import bernielib as bl

from mock import patch

class bernielib_test_case(unittest.TestCase):
    
    
    @patch('purify.bl.time.sleep')
    @patch('purify.bl.serial.Serial')
    def setUp(self, mock_serial, mock_sleep):
        #bl.time.sleep = mock.MagicMock()
        #bl.serial.Serial = mock.MagicMock()
        self.ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        self.sample_type = 'test_sample_type'
        self.sample_name = 'test_sample'
        self.mix_script_filename = 'test_mix_script.csv'
    
    
    def test_isLowVolumeUptakeNeeded(self):
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 1000)
        self.assertEqual(s1.getCloseToBottomVol(), 50)
        self.assertEqual(s1.getVolume(), 1000)
        self.assertEqual(s1.getExtraImmersionVol(), 200)
        
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(0)
        self.assertFalse(low_volume_uptake_needed)
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(250)
        self.assertFalse(low_volume_uptake_needed)
        
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 200)
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(0)
        self.assertTrue(low_volume_uptake_needed)
    
    def test_creteTestSample(self):
        s1 = bl.createSample(self.sample_type, self.sample_name, self.ber.samples_rack, 1, 0, 0)
        
        self.assertEqual(s1.name, self.sample_name)
        self.assertEqual(s1.stype.name, self.sample_type)
        self.assertEqual(s1.rack, self.ber.samples_rack)
        self.assertEqual(s1.getWell(), (1, 0))
        self.assertEqual(s1.getVolume(), 0)

    def test_SaveSampleTypeSetting(self):
        s1 = bl.createSample(self.sample_type, self.sample_name, self.ber.samples_rack, 1, 0, 0)
        
        s1.stype._setSetting('new_setting_name', 'asdf')
        
        self.assertTrue(os.path.exists(self.sample_type+'.json'))
        self.assertEqual(s1.stype.data['new_setting_name'], 'asdf')
        self.assertEqual(s1.stype._getSetting('new_setting_name'), 'asdf')
    
    def test_MixScriptSettings(self):
        # Creating mock mix script file
        line1 = "Height,H_relative_to,Plunger_pos,dx,dy,min_vol_condition,max_vol_condition,delay,comment\n"
        line2 = "0,top,down,0,0,0,1700,0.5,Initially lowering the plunger\n"
        line3 = "1,bottom,up,0,0,0,250,0.5,mixing in place\n"
        
        with open(self.mix_script_filename, mode='a') as csv_file:
            csv_file.write(line1)
            csv_file.write(line2)
            csv_file.write(line3)
        
        # Making sure the file was in fact created
        self.assertTrue(os.path.exists(self.mix_script_filename))
        # Making sure the file reads
        df = pd.read_csv(self.mix_script_filename)
        self.assertEqual(df['Height'][0], 0)
        self.assertEqual(df['Height'][1], 1)
        self.assertEqual(df['H_relative_to'][0], 'top')
        self.assertEqual(df['H_relative_to'][1], 'bottom')
            
        # Creating a sample_name
        s1 = bl.createSample(self.sample_type, self.sample_name, self.ber.samples_rack, 1, 0, 0)
        
        # Saving mix script file path
        s1.stype.setMixScriptFilePath(self.mix_script_filename)
        # Testing whether file name was saved
        self.assertTrue(os.path.exists(self.sample_type+'.json'))
        self.assertEqual(s1.stype.data['mix_script_file_path'], self.mix_script_filename)
        self.assertEqual(s1.stype.getMixScriptFilePath(), self.mix_script_filename)
        # Testing whether the dataframe obtained through getMixScript is correct
        df = s1.stype.getMixScript()
        self.assertEqual(df['Height'][0], 0)
        self.assertEqual(df['Height'][1], 1)
        self.assertEqual(df['H_relative_to'][0], 'top')
        self.assertEqual(df['H_relative_to'][1], 'bottom')

    def test_createSamplesToPurifyList_generating_from_volume_list(self):
        
        samples_list = bl.createSamplesToPurifyList(self.ber, [30, 40, 50])
        
        self.assertEqual(samples_list[0].getVolume(), 30)
        self.assertEqual(samples_list[1].getVolume(), 40)
        self.assertEqual(samples_list[2].getVolume(), 50)
        
        self.assertEqual(samples_list[0].getWell(), (1, 0))
        self.assertEqual(samples_list[1].getWell(), (1, 1))
        self.assertEqual(samples_list[2].getWell(), (1, 2))
        
    def test_createSamplesToPurifyList_generating_from_positions_list(self):
        samples_list = bl.createSamplesToPurifyList(self.ber, [30, 40, 50], [6, 7, 8])
        
        self.assertEqual(samples_list[0].getVolume(), 30)
        self.assertEqual(samples_list[1].getVolume(), 40)
        self.assertEqual(samples_list[2].getVolume(), 50)
        
        self.assertEqual(samples_list[0].getWell(), (1, 6))
        self.assertEqual(samples_list[1].getWell(), (1, 7))
        self.assertEqual(samples_list[2].getWell(), (1, 8))
        
    def test_createSamplesToPurifyList_generating_from_number_of_tubes(self):
        samples_list = bl.createSamplesToPurifyList(self.ber, number_of_tubes=3)
        
        self.assertEqual(samples_list[0].getVolume(), 0)
        self.assertEqual(samples_list[1].getVolume(), 0)
        self.assertEqual(samples_list[2].getVolume(), 0)
        
        self.assertEqual(samples_list[0].getWell(), (1, 0))
        self.assertEqual(samples_list[1].getWell(), (1, 1))
        self.assertEqual(samples_list[2].getWell(), (1, 2))
    
    def test_createSamplesToPurifyList__start_from_position(self):
        samples_list = bl.createSamplesToPurifyList(self.ber, [30, 40, 50], start_from_position=6)
        
        self.assertEqual(samples_list[0].getVolume(), 30)
        self.assertEqual(samples_list[1].getVolume(), 40)
        self.assertEqual(samples_list[2].getVolume(), 50)
        
        self.assertEqual(samples_list[0].getWell(), (1, 6))
        self.assertEqual(samples_list[1].getWell(), (1, 7))
        self.assertEqual(samples_list[2].getWell(), (1, 8))
    
    def tearDown(self):
        try:
            os.remove(self.sample_type+'.json')
        except:
            pass
            
        try:
            os.remove(self.sample_name+'.json')
        except:
            pass

        try:
            os.remove(self.mix_script_filename)
        except:
            pass
            
        try:
            self.ber.close()
        except:
            pass

        try:
            del self.ber
        except:
            pass
        
if __name__ == '__main__':
    unittest.main(verbosity=2)
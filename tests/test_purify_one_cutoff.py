import unittest
import os
import mock
import logging
import csv
import time
from shutil import copyfile
import bernielib

import purify as ponec
import bernielib as bl

from mock import patch

#TODO: Beads volume for the first stage must be less than for the second stage.


class one_step_cutoff_test_case(unittest.TestCase):

    @patch('purify.bl.robot._writeAndWait')
    @patch('time.sleep', return_value=None)
    @patch('bernielib.time')
    @patch('purify.time.sleep')
    @patch('serial.Serial')
    def setUp(self, mock_serial, mock_sleep, mock_sleep2, mock_sleep3, mock_writeAndWait):
        logging.disable(logging.CRITICAL)
        self.ber = ponec.bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        self.ber._writeAndWait = mock_writeAndWait
        

    def tearDown(self):
        try:
            self.ber.close()
        except:
            pass

        try:
            del self.ber
        except:
            pass      
        logging.disable(logging.NOTSET)


    @patch('purify.bl.robot.dumpTipToWaste')
    @patch('purify.bl.robot.pickUpNextTip')
    @patch('purify.bl.robot.move')
    @patch('purify.bl.robot.transferLiquid')
    def test_transferSampleToSecondStage(self, mock_transferLiquid, mock_move,
            mock_pickUpNextTip, mock_dumpTipToWaste):
        
        filepath = r'.\tests\samplesheet_2stages__beads_vol.csv'
        s = ponec.settings(filepath)
        tubes = ponec.items(self.ber, s)
        samples_list = tubes.samples_list
        intermediate_list = tubes.intermediate_list
        sample = samples_list[0]
        intermediate = intermediate_list[0]
        
        ponec.transferSampleToSecondStage(self.ber, sample, intermediate)
        
        self.assertTrue(mock_transferLiquid.called)
        #self.assertTrue(self.ber.transferLiquid.called)
        
        call = self.ber.transferLiquid.mock_calls[0]
        expected = mock.call(source=sample, destination=intermediate, 
                             volume=sample.getVolume(), dry_tube=True, safe_z=50, delay=0.5,
                             source_tube_radius=2.0)
        
        self.assertEqual(call, expected)

    """
    @patch('time.sleep')
    @patch('purify.separateEluateAllTubes')
    @patch('purify.eluteAllSamples')
    @patch('purify.waitAfterTimestamp')
    @patch('purify.add80PctEthanol')
    @patch('purify.removeSupernatantAllSamples')
    @patch('purify.bl.robot.moveMagnetsTowardsTube')
    @patch('purify.mixManySamples')
    @patch('purify.bl.robot.setSpeedPipette')
    @patch('purify.addBeadsToAll')
    def test_purifyOneCutoff__pipetting_delay__addBeadsToAll(self, 
                                                             mock_addBeadsToAll,
                                                             mock_setSpeedPipette,
                                                             mock_mixManySamples,
                                                             mock_moveMagnetsTowardsTube,
                                                             mock_removeSupernatantAllSamples,
                                                             mock_add80PctEthanol,
                                                             mock_waitAfterTimestamp,
                                                             mock_eluteAllSamples,
                                                             mock_separateEluateAllTubes,
                                                             mock_sleep):
        self.ber.setSpeedPipette = mock_setSpeedPipette
        self.ber.setSpeedPipette = mock_moveMagnetsTowardsTube
        
        filepath = r'.\factory_default\samplesheet.csv'
        s = ponec.settings(filepath)
        ponec.purify_one_cutoff(self.ber, s)
        
        mock_addBeadsToAll_first_call_first_arg = mock_addBeadsToAll.mock_calls[0][1][0]
        mock_addBeadsToAll_first_call_delay_arg = mock_addBeadsToAll.mock_calls[0][2]['delay']
        self.assertEqual(self.ber, mock_addBeadsToAll_first_call_first_arg)
        self.assertEqual(1, mock_addBeadsToAll_first_call_delay_arg)
    """        
    
    
    """
    def test_transferAllSamplesToSecondStage(self):
        
        real_transferSampleToSecondStage = ponec.transferSampleToSecondStage
        ponec.transferSampleToSecondStage = mock.MagicMock()
        
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        intermediate_list = ponec.initIntermediate(self.ber, settings)
        
        ponec.transferAllSamplesToSecondStage(self.ber, samples_list, intermediate_list)
        
        self.assertTrue(ponec.transferSampleToSecondStage.called)
        
        
        source1 = ponec.transferSampleToSecondStage.mock_calls[0][1][1]
        dest1 = ponec.transferSampleToSecondStage.mock_calls[0][1][2]
        source2 = ponec.transferSampleToSecondStage.mock_calls[1][1][1]
        dest2 = ponec.transferSampleToSecondStage.mock_calls[1][1][2]
        source3 = ponec.transferSampleToSecondStage.mock_calls[2][1][1]
        dest3 = ponec.transferSampleToSecondStage.mock_calls[2][1][2]
        
        self.assertEqual(source1, samples_list[0])
        
        ponec.transferSampleToSecondStage = real_transferSampleToSecondStage
        assertEqual(ponec.transferSampleToSecondStage, real_transferSampleToSecondStage)
    """

    @patch('time.sleep')
    @patch('purify.transferAllSamplesToSecondStage')
    @patch('purify.separateEluateAllTubes')
    @patch('purify.eluteAllSamples')
    @patch('purify.waitAfterTimestamp')
    @patch('purify.add80PctEthanol')
    @patch('purify.removeSupernatantAllSamples')
    @patch('purify.bl.robot.moveMagnetsAway')
    @patch('purify.bl.robot.moveMagnetsTowardsTube')
    @patch('purify.mixManySamples')
    @patch('purify.bl.robot.setSpeedPipette')
    @patch('purify.addBeadsToAll')    
    def test_purifyTwoCutoffs_beads_volumes(self,
                                            mock_addBeadsToAll,
                                            mock_setSpeedPipette,
                                            mock_mixManySamples,
                                            mock_moveMagnetsTowardsTube,
                                            mock_moveMagnetsAway,
                                            mock_removeSupernatantAllSamples,
                                            mock_add80PctEthanol,
                                            mock_waitAfterTimestamp,
                                            mock_eluteAllSamples,
                                            mock_separateEluateAllTubes,
                                            mock_transferAllSamplesToSecondStage,
                                            mock_sleep,
                                            ):
        
        self.ber.moveMagnetsTowardsTube = mock_moveMagnetsTowardsTube
        self.ber.moveMagnetsAway = mock_moveMagnetsAway
        self.ber.setSpeedPipette = mock_setSpeedPipette
        
        filepath = r'.\tests\samplesheet_2stages__beads_vol.csv'
        s = ponec.settings(filepath)
        
        ponec.purifyTwoCutoffs(self.ber, s)
        
        # Volumes
        volume_list_received_at_first_AddBeadsToAll = mock_addBeadsToAll.mock_calls[0][1][2]
        volume_list_received_at_second_AddBeadsToAll = mock_addBeadsToAll.mock_calls[1][1][2]
        self.assertEqual(volume_list_received_at_first_AddBeadsToAll, [80, 70, 60])
        self.assertEqual(volume_list_received_at_second_AddBeadsToAll, [140, 110, 67])
        
        # Mixing
        samples_list_1st_abs_mix = mock_mixManySamples.mock_calls[0][1][1]
        samples_list_2nd_abs_mix = mock_mixManySamples.mock_calls[1][1][1]
        samples_mix_elution = mock_mixManySamples.mock_calls[2][1][1]
        self.assertEqual(samples_list_1st_abs_mix[0].getWell(), (1, 0))
        self.assertEqual(samples_list_1st_abs_mix[1].getWell(), (1, 1))
        self.assertEqual(samples_list_1st_abs_mix[2].getWell(), (1, 2))
        self.assertEqual(samples_list_2nd_abs_mix[0].getWell(), (1, 6))
        self.assertEqual(samples_list_2nd_abs_mix[1].getWell(), (1, 7))
        self.assertEqual(samples_list_2nd_abs_mix[2].getWell(), (1, 8))
        self.assertEqual(samples_mix_elution[0].getWell(), (1, 6))
        self.assertEqual(samples_mix_elution[1].getWell(), (1, 7))
        self.assertEqual(samples_mix_elution[2].getWell(), (1, 8))


    @patch('purify.removeSupernatantAllSamples')
    @patch('purify.waitAfterTimestamp')
    @patch('purify.bl.robot.setSpeedPipette')
    @patch('purify.add80PctEthanol')
    def test_ethanolWash(self,
                         mock_add80PctEthanol,
                         mock_setSpeedPipette,
                         mock_waitAfterTimestamp,
                         mock_removeSupernatantAllSamples,
                         ):
        # Loading necessary parameters
        filepath = r'.\factory_default\samplesheet.csv'
        s = ponec.settings(filepath)
        tubes = ponec.items(self.ber, s)
        
        # Running the function to be tested
        ponec.ethanolWash(self.ber, s, tubes.samples_list, tubes.ethanol, tubes.waste)
        
        # Making sure the reagents (ethanol and waste) are where they should be
        ethanol_obj_provided_to_1st_add80PctEthanol = mock_add80PctEthanol.mock_calls[0][1][2]
        self.assertEqual(ethanol_obj_provided_to_1st_add80PctEthanol, tubes.ethanol)
        ethanol_sample_well = ethanol_obj_provided_to_1st_add80PctEthanol.getWell()
        self.assertEqual(ethanol_sample_well, (0,2))
        self.assertEqual(ethanol_obj_provided_to_1st_add80PctEthanol.rack, self.ber.reagents_rack)
        
        ethanol_obj_provided_to_2nd_add80PctEthanol = mock_add80PctEthanol.mock_calls[1][1][2]
        self.assertEqual(ethanol_obj_provided_to_2nd_add80PctEthanol, tubes.ethanol)
        ethanol_sample_well = ethanol_obj_provided_to_2nd_add80PctEthanol.getWell()
        self.assertEqual(ethanol_sample_well, (0,2))
        self.assertEqual(ethanol_obj_provided_to_2nd_add80PctEthanol.rack, self.ber.reagents_rack)
        
        # Testing the samples positions
        # First call to add 80% ethanol
        s1, s2, s3 = mock_add80PctEthanol.mock_calls[0][1][1]
        self.assertEqual(s1, tubes.samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, tubes.samples_list[1])
        self.assertEqual(s3, tubes.samples_list[2])
        self.assertEqual(s1.getWell(), (1, 0))  # Samples are in the right wells
        self.assertEqual(s2.getWell(), (1, 1))
        self.assertEqual(s3.getWell(), (1, 2))
        self.assertEqual(s1.rack, self.ber.samples_rack)
        self.assertEqual(s2.rack, self.ber.samples_rack)
        self.assertEqual(s3.rack, self.ber.samples_rack)
        
        # Second call to add 80% ethanol
        s1, s2, s3 = mock_add80PctEthanol.mock_calls[1][1][1]
        self.assertEqual(s1, tubes.samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, tubes.samples_list[1])
        self.assertEqual(s3, tubes.samples_list[2])
        self.assertEqual(s1.getWell(), (1, 0))  # Samples are in the right wells
        self.assertEqual(s2.getWell(), (1, 1))
        self.assertEqual(s3.getWell(), (1, 2))
        self.assertEqual(s1.rack, self.ber.samples_rack)
        self.assertEqual(s2.rack, self.ber.samples_rack)
        self.assertEqual(s3.rack, self.ber.samples_rack)
        
        # Supernatant removed after 1st wash
        s1, s2, s3 = mock_removeSupernatantAllSamples.mock_calls[0][1][1]
        self.assertEqual(s1, tubes.samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, tubes.samples_list[1])
        self.assertEqual(s3, tubes.samples_list[2])

    
    @patch('time.sleep')
    @patch('purify.separateEluateAllTubes')
    @patch('purify.bl.robot.moveMagnetsAway')
    @patch('purify.bl.robot.moveMagnetsTowardsTube')
    @patch('purify.mixManySamples')
    @patch('purify.eluteAllSamples')
    @patch('purify.bl.robot.setSpeedPipette')
    def test_elution(self, 
                     mock_setSpeedPipette,
                     mock_eluteAllSamples,
                     mock_mixManySamples,
                     mock_moveMagnetsTowardsTube,
                     mock_moveMagnetsAway,
                     mock_separateEluateAllTubes,
                     mock_sleep,
                     ):
        # Loading necessary parameters
        filepath = r'.\factory_default\samplesheet.csv'
        s = ponec.settings(filepath)
        tubes = ponec.items(self.ber, s)
        
        # Running the function to be tested
        ponec.elution(self.ber, s, tubes)
        
        self.assertEqual(mock_eluteAllSamples.mock_calls, 
            [mock.call(self.ber, s, tubes, pipetting_delay=1.0)])
            
    
    
class purify_settings_test_case(unittest.TestCase):
    
    def setUp(self):
        # Creating generic csv file data
        # mock .csv data path (in tests folder).
        self.mock_csv_path = '.\\tests\\mock_sample_sheet_generic.csv'
        self.row_dict = {
            'Parameters': ['Parameters', 
                           'Comment', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            'Text line 1': ['Text line'],
            'Number of cutoffs': ['Number of cutoffs', '', 1],
        }
        
        
    def tearDown(self):
        self.delTempSettingsFile()
        return
    
    def createTempSettingsFile(self):
        temp_dict = self.row_dict.copy()
        with open(self.mock_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(temp_dict['Parameters'])
            temp_dict.pop('Parameters')
            for key in temp_dict.keys():
                writer.writerow(temp_dict[key])
        del temp_dict
    
    def delTempSettingsFile(self):
        try:
            os.remove(self.mock_csv_path)
        except:
            pass
    
    def test__test_creating_mockup_csv(self):
        self.createTempSettingsFile()
        # Testing its own mock csv file creation.
        self.assertTrue(os.path.exists(self.mock_csv_path))
    
    @patch('purify.settings.loadIndividualSettings')
    def test_init(self, mock_loadIndividualSettings):
        self.createTempSettingsFile()
        s = ponec.settings(self.mock_csv_path)
        for row in s.settings:
            self.assertTrue('Parameters' in row)
            self.assertTrue('0' in row)
            param = row['Parameters']
            if param == 'Number of cutoffs':
                self.assertEqual(row['0'], '1')
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getRowWithParameter(self, mock_loadIndividualSettings):
        self.createTempSettingsFile()
        s = ponec.settings(self.mock_csv_path)
        row = s.getRowWithParameter('Number of cutoffs')
        self.assertEqual(row['0'], '1')
        
    @patch('purify.settings.loadIndividualSettings')
    def test_returnSampleParameter(self, mock_loadIndividualSettings):
        self.createTempSettingsFile()
        s = ponec.settings(self.mock_csv_path)
        val = s.returnSampleParameter('Number of cutoffs', 0)
        self.assertEqual(val, 1.0)
        self.assertEqual(val, 1)
    
    @patch('purify.settings.loadIndividualSettings')
    def test_returnProtocolParameter(self, mock_loadIndividualSettings):
        self.createTempSettingsFile()
        s = ponec.settings(self.mock_csv_path)
        val = s.returnProtocolParameter('Number of cutoffs')
        self.assertEqual(val, 1)


    def prep_settingsFile(self, parameter, value_list):
        self.row_dict[parameter] = [parameter, ''] + value_list
        self.createTempSettingsFile()

    @patch('purify.settings.loadIndividualSettings')
    def test_positionsToPurify(self, mock_loadIndividualSettings):
        self.prep_settingsFile('Initial sample volume', 
            [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        positions = s.positionsToPurify()
        self.assertEqual(positions, [0, 1, 2])
        self.delTempSettingsFile()
        
        self.prep_settingsFile('Initial sample volume', 
            [-1, -1, 60, 20, 30, -1, -1, -1, 0, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        positions = s.positionsToPurify()
        self.assertEqual(positions, [2, 3, 4])
        self.delTempSettingsFile()
        
        self.prep_settingsFile('Initial sample volume', 
            [0, 0, 0, 0, 0, -1, -1, -1, 0, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        positions = s.positionsToPurify()
        self.assertEqual(positions, [])
        self.delTempSettingsFile()
        
    @patch('purify.settings.loadIndividualSettings')
    def test_positionsToPurify2ndStage(self, mock_loadIndividualSettings):
        self.prep_settingsFile('Initial sample volume', 
            [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        positions = s.positionsToPurify2ndStage()
        self.assertEqual(positions, [6, 7, 8])
        self.delTempSettingsFile()

    @patch('purify.settings.loadIndividualSettings')
    def test_positionsToPurify2ndStage(self, mock_loadIndividualSettings):
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        values = s._returnSampleParameterList(param)
        self.assertEqual(values, [100, 29, 50])

    @patch('purify.settings.loadIndividualSettings')
    def test_returnPort(self, mock_loadIndividualSettings):
        ls_param = 'Load cells controller port'
        crt_param = 'Cartesian controller port'
        
        self.prep_settingsFile(ls_param, ['auto'])
        self.prep_settingsFile(crt_param, ['auto'])
        s = ponec.settings(self.mock_csv_path)
        ls_port = s.returnPort(kind=ls_param)
        crt_port = s.returnPort(kind=crt_param)
        self.assertEqual(ls_port, None)
        self.assertEqual(crt_port, None)
        self.delTempSettingsFile()
        
        self.prep_settingsFile(ls_param, ['COM1'])
        self.prep_settingsFile(crt_param, ['COM2'])
        s = ponec.settings(self.mock_csv_path)
        ls_port = s.returnPort(kind=ls_param)
        crt_port = s.returnPort(kind=crt_param)
        self.assertEqual(ls_port, 'COM1')
        self.assertEqual(crt_port, 'COM2')
        self.delTempSettingsFile()
        
    @patch('purify.settings.loadIndividualSettings')
    def test_getRackName(self, mock_loadIndividualSettings):
        logging.disable(logging.CRITICAL)
    
        beads = 'Beads tube rack'
        waste = 'Waste tube rack'
        eluent = 'Eluent tube rack'
        ethanol = 'Ethanol tube rack'
        
        self.prep_settingsFile(beads, ['reagents'])
        self.prep_settingsFile(waste, ['reagents'])
        self.prep_settingsFile(eluent, ['reagents'])
        self.prep_settingsFile(ethanol, ['reagents'])
        s = ponec.settings(self.mock_csv_path)
        val = s._getRackName('Beads')
        self.assertEqual('reagents', val)
        val = s._getRackName('Waste')
        self.assertEqual('reagents', val)
        val = s._getRackName('Eluent')
        self.assertEqual('reagents', val)
        val = s._getRackName('Ethanol')
        self.assertEqual('reagents', val)
        self.delTempSettingsFile()
        
        self.prep_settingsFile(beads, ['samples'])
        s = ponec.settings(self.mock_csv_path)
        val = s._getRackName('Beads')
        self.assertEqual('samples', val)
        self.delTempSettingsFile()
        
        self.prep_settingsFile(beads, ['asdf'])
        s = ponec.settings(self.mock_csv_path)
        val = s._getRackName('Beads')
        self.assertEqual(None, val)
        self.delTempSettingsFile()
    
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getTubePositionInRack(self, mock_loadIndividualSettings):
        self.prep_settingsFile('Beads tube column', [0])
        self.prep_settingsFile('Beads tube well', [4])
        
        s = ponec.settings(self.mock_csv_path)
        col, row = s._getTubePositionInRack('Beads')
        self.assertEqual(col, 0)
        self.assertEqual(row, 4)
    
    
    def prep_createBeadsVolSettings(self, number_of_cutoffs=1):
        beads_vol_upper_setting = 'Beads volume upper cutoff'
        fraction_upper_setting = 'Fraction upper cutoff'
        dna_size_upper_cutoff_setting = 'DNA size upper cutoff'
        beads_vols_upper = [30, 20, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, ]
        fracs_upper = [0.5, 0.6, 0.55, -1, -1, -1, -1, -1, -1, -1, -1, -1, ]
        dna_cutoffs_upper = [900, 800, 700, -1, -1, -1, -1, -1, -1, -1, -1, -1,]
        beads_vol_setting = 'Beads volume'
        fraction_setting = 'Fraction'
        dna_size_cutoff_setting = 'DNA size cutoff'
        beads_vols = [15, 31, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, ]
        fracs = [1.0, 0.9, 1.5, -1, -1, -1, -1, -1, -1, -1, -1, -1, ]
        dna_cutoffs = [150, 300, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1,]
        self.prep_settingsFile(beads_vol_setting, beads_vols)
        self.prep_settingsFile(fraction_setting, fracs)
        self.prep_settingsFile(dna_size_cutoff_setting, dna_cutoffs)
        self.prep_settingsFile(beads_vol_upper_setting, beads_vols_upper)
        self.prep_settingsFile(fraction_upper_setting, fracs_upper)
        self.prep_settingsFile(dna_size_upper_cutoff_setting, dna_cutoffs_upper)
        self.prep_settingsFile('Number of cutoffs', [number_of_cutoffs])
        
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsSetting(self, mock_loadIndividualSettings):
    
        self. prep_createBeadsVolSettings(1)
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        v = s._getBeadsSetting(0, 1, 'Beads volume')
        self.assertEqual(15, v)
        v = s._getBeadsSetting(1, 1, 'Beads volume')
        self.assertEqual(31, v)
        v = s._getBeadsSetting(2, 1, 'Beads volume')
        self.assertEqual(22, v)


    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsSetting_2stages(self, mock_loadIndividualSettings):
        
        self. prep_createBeadsVolSettings(2)
    
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        v = s._getBeadsSetting(0, 1, 'Beads volume')
        self.assertEqual(30, v)
        v = s._getBeadsSetting(1, 1, 'Beads volume')
        self.assertEqual(20, v)
        v = s._getBeadsSetting(2, 1, 'Beads volume')
        self.assertEqual(25, v) 
        self.delTempSettingsFile()
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsSetting_2stages_both(self, mock_loadIndividualSettings):
        
        self. prep_createBeadsVolSettings(2)
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        
        # 1st stage
        v = s._getBeadsSetting(0, 1, 'Beads volume')
        self.assertEqual(30, v)
        v = s._getBeadsSetting(1, 1, 'Beads volume')
        self.assertEqual(20, v)
        v = s._getBeadsSetting(2, 1, 'Beads volume')
        self.assertEqual(25, v)
        f = s._getBeadsSetting(0, 1, 'Fraction')
        self.assertEqual(0.5, f)
        f = s._getBeadsSetting(1, 1, 'Fraction')
        self.assertEqual(0.6, f)
        f = s._getBeadsSetting(2, 1, 'Fraction')
        self.assertEqual(0.55, f)
        dnasize = s._getBeadsSetting(0, 1, 'DNA size')
        self.assertEqual(900, dnasize)
        dnasize = s._getBeadsSetting(1, 1, 'DNA size')
        self.assertEqual(800, dnasize)
        dnasize = s._getBeadsSetting(2, 1, 'DNA size')
        self.assertEqual(700, dnasize)
        # 2nd stage
        v = s._getBeadsSetting(0, 2, 'Beads volume')
        self.assertEqual(15, v)
        v = s._getBeadsSetting(1, 2, 'Beads volume')
        self.assertEqual(31, v)
        v = s._getBeadsSetting(2, 2, 'Beads volume')
        self.assertEqual(22, v)
        f = s._getBeadsSetting(0, 2, 'Fraction')
        self.assertEqual(1.0, f)
        f = s._getBeadsSetting(1, 2, 'Fraction')
        self.assertEqual(0.9, f)
        f = s._getBeadsSetting(2, 2, 'Fraction')
        self.assertEqual(1.5, f)
        dnasize = s._getBeadsSetting(0, 2, 'DNA size')
        self.assertEqual(150, dnasize)
        dnasize = s._getBeadsSetting(1, 2, 'DNA size')
        self.assertEqual(300, dnasize)
        dnasize = s._getBeadsSetting(2, 2, 'DNA size')
        self.assertEqual(100, dnasize)
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsVolDirectly(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(2)
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        
        v = s._getBeadsVolDirectly(0, 1)
        self.assertEqual(30, v)
        v = s._getBeadsVolDirectly(1, 1)
        self.assertEqual(20, v)
        v = s._getBeadsVolDirectly(2, 1)
        self.assertEqual(25, v)
        v = s._getBeadsVolDirectly(0, 2)
        self.assertEqual(15, v)
        v = s._getBeadsVolDirectly(1, 2)
        self.assertEqual(31, v)
        v = s._getBeadsVolDirectly(2, 2)
        self.assertEqual(22, v)
        
        self.delTempSettingsFile()
        del s
        
        self. prep_createBeadsVolSettings(1)
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        
        v = s._getBeadsVolDirectly(0, 1)
        self.assertEqual(15, v)
        v = s._getBeadsVolDirectly(1, 1)
        self.assertEqual(31, v)
        v = s._getBeadsVolDirectly(2, 1)
        self.assertEqual(22, v)
    
    @patch('purify.settings.loadIndividualSettings')
    def test_calcBeadsVolFromFrac(self, mock_loadIndividualSettings):
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._calcBeadsVolFromFrac(0, 0.5)
        self.assertEqual(v, 50)
        v = s._calcBeadsVolFromFrac(2, 0.5)
        self.assertEqual(v, 25)
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsVolUsingFraction(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(1)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._getBeadsVolUsingFraction(0, 1)
        self.assertEqual(v, 100)
        v = s._getBeadsVolUsingFraction(1, 1)
        self.assertEqual(v, 29*0.9)
        v = s._getBeadsVolUsingFraction(2, 1)
        self.assertEqual(v, 50*1.5)
        
        
        self.prep_createBeadsVolSettings(2)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._getBeadsVolUsingFraction(0, 1)
        self.assertEqual(v, 100*0.5)
        v = s._getBeadsVolUsingFraction(1, 1)
        self.assertEqual(v, 29*0.6)
        v = s._getBeadsVolUsingFraction(2, 1)
        self.assertEqual(v, 50*0.55)
        v = s._getBeadsVolUsingFraction(0, 2)
        self.assertEqual(v, 100*(1.0-0.5))
        v = s._getBeadsVolUsingFraction(1, 2)
        self.assertEqual(v, 29*(0.9-0.6))
        v = s._getBeadsVolUsingFraction(2, 2)
        self.assertEqual(v, 50*(1.5-0.55))
        
    
    @patch('purify.settings.loadIndividualSettings')
    def test_calcBeadVolFractionFromDNACutoff(self, mock_loadIndividualSettings):
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        f = s._calcBeadVolFractionFromDNACutoff(1000)
        
        a,b,c = bl.getBeadsVolumeCoef()
        f_expected = a + b / 1000 + c / 1000 ** 2
        
        self.assertEqual(f, f_expected)
        
        
        f = s._calcBeadVolFractionFromDNACutoff(160)
        
        a,b,c = bl.getBeadsVolumeCoef()
        f_expected = a + b / 160 + c / 160 ** 2
        
        self.assertEqual(f, f_expected)
        

    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsVolUsingDNACutoff(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(1)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        a,b,c = bl.getBeadsVolumeCoef()
        f_expected = a + b / 150 + c / 150 ** 2
        v = s._getBeadsVolUsingDNACutoff(0, 1)
        self.assertEqual(v, f_expected*100)
        self.assertFalse(v == 0)
        
        f_expected = a + b / 300 + c / 300 ** 2
        v = s._getBeadsVolUsingDNACutoff(1, 1)
        self.assertEqual(v, f_expected*29)
        
        f_expected = a + b / 100 + c / 100 ** 2
        v = s._getBeadsVolUsingDNACutoff(2, 1)
        self.assertEqual(v, f_expected*50)
    
        self.delTempSettingsFile()
        del s
        
        self.prep_createBeadsVolSettings(2)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        f_expected = a + b / 900 + c / 900 ** 2
        v = s._getBeadsVolUsingDNACutoff(0, 1)
        self.assertEqual(v, f_expected*100)
        
        f_expected = a + b / 800 + c / 800 ** 2
        v = s._getBeadsVolUsingDNACutoff(1, 1)
        self.assertEqual(v, f_expected*29)
        
        f_expected = a + b / 700 + c / 700 ** 2
        v = s._getBeadsVolUsingDNACutoff(2, 1)
        self.assertEqual(v, f_expected*50)
        
    @patch('purify.settings.loadIndividualSettings')
    def test__beadsVolNotValid(self, mock_loadIndividualSettings):
        self.createTempSettingsFile()
        s = ponec.settings(self.mock_csv_path)
        
        self.assertFalse(s._beadsVolNotValid(100))
        self.assertFalse(s._beadsVolNotValid(947))
        self.assertTrue(s._beadsVolNotValid(0))
        self.assertTrue(s._beadsVolNotValid(None))
    
    @patch('purify.settings.loadIndividualSettings')
    def test__getBeadsVolume_1stage(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(1)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, 15)
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, 31)
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, 22)
        
        # Rewriting the settings file. 
        # Now the function should calculate volume from the initial volume and fraction
        param = 'Beads volume'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, 100)
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, 29*0.9)
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, 50*1.5)
        
        # Rewriting the settings file. 
        # Now the function should calculate volume from the DNA cutoff value
        param = 'Fraction'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        a,b,c = bl.getBeadsVolumeCoef()
        
        expected_dna_cutoff = 150
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 100 * f_expected
        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, v_expected)
        
        expected_dna_cutoff = 300
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 29 * f_expected
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, v_expected)
        
        expected_dna_cutoff = 100
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 50 * f_expected
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, v_expected)
    

    @patch('purify.settings.loadIndividualSettings')
    def test__getBeadsVolume_2stage(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(2)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')

        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, 30)
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, 20)
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, 25)
        
        v = s._getBeadsVolume(0, 2)
        self.assertEqual(v, 15)
        v = s._getBeadsVolume(1, 2)
        self.assertEqual(v, 31)
        v = s._getBeadsVolume(2, 2)
        self.assertEqual(v, 22)
        
        
        # Rewriting the settings file. 
        # Now the function should calculate volume from the initial volume and fraction
        param = 'Beads volume'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        param = 'Beads volume upper cutoff'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, 100*0.5)
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, 29*0.6)
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, 50*0.55)
        
        v = s._getBeadsVolume(0, 2)
        self.assertEqual(v, 100*(1.0-0.5))
        v = s._getBeadsVolume(1, 2)
        self.assertEqual(v, 29*(0.9-0.6))
        v = s._getBeadsVolume(2, 2)
        self.assertEqual(v, 50*(1.5-0.55))
        
        # Rewriting the settings file. 
        # Now the function should calculate volume from the initial volume and DNA cutoff
        param = 'Fraction'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        param = 'Fraction upper cutoff'
        self.prep_settingsFile(param, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        a,b,c = bl.getBeadsVolumeCoef()
        
        expected_dna_cutoff = 900
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 100 * f_expected
        v = s._getBeadsVolume(0, 1)
        self.assertEqual(v, v_expected)
        exp_dna_cutoff_2 = 150
        f_expected_2 = a + b / exp_dna_cutoff_2 + c / exp_dna_cutoff_2 ** 2
        v_expected_2 = 100 * (f_expected_2 - f_expected)
        v = s._getBeadsVolume(0, 2)
        self.assertEqual(v, v_expected_2)
        
        
        expected_dna_cutoff = 800
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 29 * f_expected
        v = s._getBeadsVolume(1, 1)
        self.assertEqual(v, v_expected)
        exp_dna_cutoff_2 = 300
        f_expected_2 = a + b / exp_dna_cutoff_2 + c / exp_dna_cutoff_2 ** 2
        v_expected_2 = 29 * (f_expected_2 - f_expected)
        v = s._getBeadsVolume(1, 2)
        self.assertEqual(v, v_expected_2)
        
        expected_dna_cutoff = 700
        f_expected = a + b / expected_dna_cutoff + c / expected_dna_cutoff ** 2
        v_expected = 50 * f_expected
        v = s._getBeadsVolume(2, 1)
        self.assertEqual(v, v_expected)
        exp_dna_cutoff_2 = 100
        f_expected_2 = a + b / exp_dna_cutoff_2 + c / exp_dna_cutoff_2 ** 2
        v_expected_2 = 50 * (f_expected_2 - f_expected)
        v = s._getBeadsVolume(2, 2)
        self.assertEqual(v, v_expected_2)
    
    @patch('purify.settings.loadIndividualSettings')
    def test_getBeadsVolForAllSamples(self, mock_loadIndividualSettings):
        self.prep_createBeadsVolSettings(1)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v_list = s._getBeadsVolForAllSamples(1)
        
        self.assertEqual(v_list[0], 15)
        self.assertEqual(v_list[1], 31)
        self.assertEqual(v_list[2], 22)
        
        self.prep_createBeadsVolSettings(2)
        param = 'Initial sample volume'
        self.prep_settingsFile(param, [100, 29, 50, 0, 0, -1, -1, -1, -1, -1, -1, -1])
        
        s = ponec.settings(self.mock_csv_path)
        s.cutoffs = s.returnProtocolParameter('Number of cutoffs')
        s.initial_sample_vol_list = s._returnSampleParameterList('Initial sample volume')
        
        v_list = s._getBeadsVolForAllSamples(1)
        
        self.assertEqual(v_list[0], 30)
        self.assertEqual(v_list[1], 20)
        self.assertEqual(v_list[2], 25)
        
        v_list = s._getBeadsVolForAllSamples(2)
        
        self.assertEqual(v_list[0], 15)
        self.assertEqual(v_list[1], 31)
        self.assertEqual(v_list[2], 22)

    


class purify_items_test_case(unittest.TestCase):
    """
    Handles tests for samples, reagents and other items,
    usually a tube.
    """
    @patch('purify.bl.robot._writeAndWait')
    @patch('time.sleep', return_value=None)
    @patch('bernielib.time')
    @patch('purify.time.sleep')
    @patch('serial.Serial')
    def setUp(self, mock_serial, mock_sleep, mock_sleep2, mock_sleep3, mock_writeAndWait):
        logging.disable(logging.CRITICAL)
        self.ber = ponec.bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        csv_path = r'.\factory_default\samplesheet.csv'
        self.settings = ponec.settings(csv_path)
        
        
    def tearDown(self):
        try:
            del self.ber
        except:
            pass
        logging.disable(logging.NOTSET)

    def test_initItems(self):
        items = ponec.items(self.ber, self.settings)
        
        self.assertEqual(items.settings, self.settings)
        self.assertEqual(items.robot, self.ber)
        self.assertEqual(items.number_of_samples, 3)
        self.assertEqual(items.initial_sample_vol_list, [100, 100, 100])
        self.assertEqual(items.cutoffs, self.settings.cutoffs)
        self.assertEqual(items.samples_list[0].getVolume(), 100)
        self.assertEqual(items.samples_list[0].getWell(), (1, 0))
        self.assertEqual(items.samples_list[1].getWell(), (1, 1))
        self.assertEqual(items.samples_list[0].rack, self.ber.samples_rack)
        self.assertIsNone(items.intermediate_list)
        self.assertEqual(items.result_list[0].getVolume(), 0)
        self.assertEqual(items.result_list[0].getWell(), (0,0))
        
        self.assertEqual(items.beads.getVolume(), 3500)
        self.assertEqual(items.beads.getWell(), (0, 4))
        self.assertEqual(items.beads.rack, self.ber.reagents_rack)
        self.assertEqual(items.waste.getVolume(), 0)
        self.assertEqual(items.waste.getWell(), (0, 1))
        self.assertEqual(items.waste.rack, self.ber.reagents_rack)
        self.assertEqual(items.ethanol.getVolume(), 25000)
        self.assertEqual(items.ethanol.getWell(), (0, 2))
        self.assertEqual(items.ethanol.rack, self.ber.reagents_rack)
        self.assertEqual(items.eluent.getVolume(), 25000)
        self.assertEqual(items.eluent.getWell(), (0, 0))
        self.assertEqual(items.eluent.rack, self.ber.reagents_rack)


class purify_protocol_test_case(unittest.TestCase):
    """
    Handles tests for the protocol class.
    Protocol class handles all the protocol-related operations and data.
    """
    
    @patch('purify.bl.robot._writeAndWait')
    @patch('time.sleep', return_value=None)
    @patch('bernielib.time')
    @patch('purify.time.sleep')
    @patch('serial.Serial')
    def setUp(self, mock_serial, mock_sleep, mock_sleep2, mock_sleep3, mock_writeAndWait):
        logging.disable(logging.CRITICAL)
        self.test_samplesheet_path = r'.\tests\samplesheet_protocol_test.csv'
        self.test_samplesheet_path_2 = r'.\tests\samplesheet_2stages_protocol_test.csv'
        copyfile(r'.\factory_default\samplesheet.csv', self.test_samplesheet_path)
        copyfile(r'.\factory_default\samplesheet_2stages.csv', self.test_samplesheet_path_2)
        self.ber = ponec.bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        self.settings = ponec.settings(self.test_samplesheet_path)
        self.settings2 = ponec.settings(self.test_samplesheet_path_2)
        
        # 11/12/2021 - default pipetting speed is 2500.0
        self.default_pipetting_speed = self.ber.getSpeedPipette()
        
    def tearDown(self):
        # Preserving the pipette speed settings, that might have been changed 
        # during failed tests.
        self.ber.setSpeedPipette(self.default_pipetting_speed)
        try:
            os.remove(self.test_samplesheet_path)
        except:
            pass
        try:
            os.remove(self.test_samplesheet_path_2)
        except:
            pass
        logging.disable(logging.NOTSET)
    
    def test_settings_file_copied(self):
        self.assertTrue(os.path.exists(self.test_samplesheet_path))

    def test__init_protocol(self):
        """
        Check whether the protocol would even initialize
        """
        p = ponec.protocol(self.ber, self.settings)
        self.assertEqual(p.robot, self.ber)
        self.assertEqual(p.settings, self.settings)
        self.assertEqual(p.tubes.samples_list[0].getVolume(), 100)
        self.assertEqual(p.default_pipette_speed, 2500.0)
        self.assertEqual(p.incubation_time, 0)


    @patch('purify.bl.robot.moveAxisDelta')
    @patch('purify.bl.robot.uptakeLiquid')
    @patch('purify.bl.robot.dumpTipToWaste')
    @patch('purify.bl.robot.transferLiquid')
    @patch('purify.bl.robot.mixByScript')
    @patch('purify.bl.robot.pickUpNextTip')
    @patch('purify.bl.robot._writeAndWait')
    @patch('serial.Serial')
    @patch('time.sleep', return_value=None)
    def test_purify(self, mock_sleep, mock_serial,
            mock_writeAndWait, mock_pickUpNextTip,
            mock_mixByScript, mock_transferLiquid, mock_dumpTipToWaste, mock_uptakeLiquid, 
            mock_moveAxisDelta):
        p = ponec.protocol(self.ber, self.settings)
        p.purify()
        p2 = ponec.protocol(self.ber, self.settings2)
        p2.purify()

    @patch('purify.protocol.elution')
    @patch('purify.protocol.ethanolWash')
    @patch('purify.protocol.removeSupernatant')
    @patch('purify.protocol.transferSamplesToSecondStage')
    @patch('purify.protocol.absorbDnaOntoBeads')
    def test_purify_two_stages(self, mock_absrobDNA, mock_transfer, mock_remsup,
                mock_etWash, mock_elution):
        p2 = ponec.protocol(self.ber, self.settings2)
        p2.purify()
        mock_transfer.assert_called()
        mock_absrobDNA.assert_called()
        mock_remsup.assert_called()
        mock_etWash.assert_called()
        mock_elution.assert_called()
    

    @patch('purify.bl.robot.pickUpNextTip')
    @patch('purify.bl.robot.dumpTipToWaste')
    @patch('purify.bl.robot.move')
    @patch('purify.bl.robot.transferLiquid')
    def test_removeSupernatant(self, mock_transferLiquid, mock_move,
            mock_dumpTipToWaste, mock_pickUpNextTip):
        p = ponec.protocol(self.ber, self.settings)
        p.removeSupernatant()

    @patch('purify.bl.robot.pickUpNextTip')
    @patch('purify.bl.robot.dumpTipToWaste')
    @patch('purify.bl.robot.move')
    @patch('purify.bl.robot.transferLiquid')
    def test_transferLiquidManyTubes(self, mock_transferLiquid, mock_move,
            mock_dumpTipToWaste, mock_pickUpNextTip):
        p = ponec.protocol(self.ber, self.settings)
        p.transferLiquidManyTubes(sources=p.tubes.samples_list, 
                destinations=p.tubes.result_list, 
                v_list=self.settings.beads_vol_1st_stage_list)
        p.transferLiquidManyTubes(sources=p.tubes.samples_list, 
                destinations=p.tubes.result_list)
    
    
    @patch('purify.bl.robot.transferLiquid')
    @patch('purify.protocol.dumpTip')
    @patch('purify.protocol.pickUpTip')
    def test_transferSamplesToSecondStage(self, mock_pickUpTip, mock_dumpTip,
            mock_transferLiquid):
        self.assertEqual(self.settings2.V_beads_list, 
                    self.settings2.beads_vol_1st_stage_list)
        
        p2 = ponec.protocol(self.ber, self.settings2)
        self.assertEqual(p2.tubes.samples_list[0].getWell(), (1, 0))
        p2.transferSamplesToSecondStage()
        self.assertEqual(self.settings2.V_beads_list, 
                    self.settings2.beads_vol_2nd_stage_list)
        self.assertEqual(p2.tubes.samples_list[0].getWell(), (1, 6))


    @patch('purify.bl.robot.moveAxisDelta')
    @patch('purify.bl.robot.uptakeLiquid')
    @patch('purify.bl.robot.dumpTipToWaste')
    @patch('purify.bl.robot.transferLiquid')
    @patch('purify.bl.robot.mixByScript')
    @patch('purify.bl.robot.pickUpNextTip')
    @patch('purify.bl.robot._writeAndWait')
    @patch('serial.Serial')
    @patch('time.sleep', return_value=None)
    @patch('purify.bl.robot.setSpeedPipette')
    def test_purify__one_stage__pipette_speed(self, 
        mock_setSpeedPipette, mock_sleep, mock_serial,
            mock_writeAndWait, mock_pickUpNextTip,
            mock_mixByScript, mock_transferLiquid, mock_dumpTipToWaste, mock_uptakeLiquid, 
            mock_moveAxisDelta):
        
        p = ponec.protocol(self.ber, self.settings)
        p.purify()
        
        # Adding beads
        self.assertEqual(mock_setSpeedPipette.mock_calls[0], mock.call(1500.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[1], mock.call(2500.0))
        # Removing sup
        self.assertEqual(mock_setSpeedPipette.mock_calls[2], mock.call(1500.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[3], mock.call(2500.0))
        # Adding ethanol 1st stage
        self.assertEqual(mock_setSpeedPipette.mock_calls[4], mock.call(2000.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[5], mock.call(2500.0))
        # Removing ethanol 1st stage
        self.assertEqual(mock_setSpeedPipette.mock_calls[6], mock.call(2000.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[7], mock.call(2500.0))
        # Adding ethanol 2nd stage
        self.assertEqual(mock_setSpeedPipette.mock_calls[8], mock.call(2000.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[9], mock.call(2500.0))
        # Removing ethanol 2nd stage
        self.assertEqual(mock_setSpeedPipette.mock_calls[10], mock.call(2000.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[11], mock.call(2500.0))
        # Adding eluent
        self.assertEqual(mock_setSpeedPipette.mock_calls[12], mock.call(1800.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[13], mock.call(2500.0))
        # Transferring eluate to the results tubes
        self.assertEqual(mock_setSpeedPipette.mock_calls[14], mock.call(1800.0))
        self.assertEqual(mock_setSpeedPipette.mock_calls[15], mock.call(2500.0))

if __name__ == '__main__':
    unittest.main()
    
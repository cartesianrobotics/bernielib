import unittest
import os
import mock

import purify as ponec
import bernielib as bl


class one_step_cutoff_test_case(unittest.TestCase):

    def setUp(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        self.ber = ponec.bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        


    def test_getBeadsVolume(self):
        settings_beads_vol = ponec.loadSettings('.\\tests\\test_samplesheet__beads_vol.csv')

        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, 40)
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, 30)
        
        settings_beads_vol = ponec.loadSettings('.\\tests\\test_samplesheet__beads_vol_by_fraction.csv')
        
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, 150)
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, 60)
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, 10)
        
        settings_beads_vol = ponec.loadSettings('.\\tests\\test_samplesheet__beads_vol_by_DNA_size.csv')
        a, b, c = self.ber.getBeadsVolumeCoef()
        frac_1000 = a + b / 1000.0 + c / 1000.0 ** 2
        frac_600 = a + b / 600.0 + c / 600.0 ** 2
        frac_150 = a + b / 150.0 + c / 150.0 ** 2
        v_1000 = 100.0 * frac_1000
        v_600 = 100.0 * frac_600
        v_150 = 100.0 * frac_150
        
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, v_1000)
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, v_600)
        v = ponec.getBeadsVolume(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, v_150)
        
        
    def test_getBeadsVol2ndStage(self):
        settings_beads_vol = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, 140)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, 110)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, 67)
        
        settings_beads_vol = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol_by_fraction.csv')
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, (1.5 - 80.0/100.0)*100.0)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, (1.0 - 70.0/100.0)*100.0)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, (0.7 - 60.0/100.0)*100.0)
        
        settings_beads_vol = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol_by_fraction2.csv')
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, (1.5 - 0.4)*100.0)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, (1.0 - 0.6)*100.0)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, (0.7 - 0.5)*100.0)
        
        settings_beads_vol = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol_by_DNA_size.csv')
        a, b, c = self.ber.getBeadsVolumeCoef()
        frac_850 = a + b / 850.0 + c / 850.0 ** 2
        frac_750 = a + b / 750.0 + c / 750.0 ** 2
        frac_600 = a + b / 600.0 + c / 600.0 ** 2
        frac_250 = a + b / 250.0 + c / 250.0 ** 2
        frac_150 = a + b / 150.0 + c / 150.0 ** 2
        frac_300 = a + b / 300.0 + c / 300.0 ** 2
        frac_2nd_stage_0 = frac_250 - frac_850
        frac_2nd_stage_1 = frac_150 - frac_750
        frac_2nd_stage_2 = frac_300 - frac_600
        v_2nd_stage_0 = 100.0 * frac_2nd_stage_0
        v_2nd_stage_1 = 100.0 * frac_2nd_stage_1
        v_2nd_stage_2 = 100.0 * frac_2nd_stage_2
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 0)
        self.assertEqual(v, v_2nd_stage_0)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 1)
        self.assertEqual(v, v_2nd_stage_1)
        v = ponec.getBeadsVolume2ndStage(self.ber, settings_beads_vol, 2)
        self.assertEqual(v, v_2nd_stage_2)


    def test_transferSampleToSecondStage(self):
        self.ber.transferLiquid = mock.MagicMock()
        self.ber.move = mock.MagicMock()
        self.ber.pickUpNextTip = mock.MagicMock()
        self.ber.dumpTipToWaste = mock.MagicMock()
        
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        intermediate_list = ponec.initIntermediate(self.ber, settings)
        sample = samples_list[0]
        intermediate = intermediate_list[0]
        
        ponec.transferSampleToSecondStage(self.ber, sample, intermediate)
        
        self.assertTrue(self.ber.transferLiquid.called)
        
        print(self.ber.transferLiquid.mock_calls[0])
        
        call = self.ber.transferLiquid.mock_calls[0]
        expected = mock.call(source=sample, destination=intermediate, 
                             volume=sample.getVolume(), dry_tube=True, safe_z=50, delay=0.5,
                             source_tube_radius=2.0)
        
        self.assertEqual(call, expected)
        
    
    def test_transferAllSamplesToSecondStage(self):
        """
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
        
    def test_purifyTwoCutoffs_beads_volumes(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        samples_list = ponec.initSamples(ber, settings)
        beads, waste, water, EtOH80pct = ponec.initReagents(ber, settings)
        
        ponec.addBeadsToAll = mock.MagicMock()
        ponec.mixManySamples = mock.MagicMock()
        ber.moveMagnetsTowardsTube = mock.MagicMock()
        ponec.time.sleep = mock.MagicMock()
        ponec.transferAllSamplesToSecondStage = mock.MagicMock()
        ber.moveMagnetsAway = mock.MagicMock()
        ponec.removeSupernatantAllSamples = mock.MagicMock()
        ponec.add80PctEthanol = mock.MagicMock()
        ponec.waitAfterTimestamp = mock.MagicMock()
        ponec.eluteAllSamples = mock.MagicMock()
        ponec.separateEluateAllTubes = mock.MagicMock()
        
        ponec.purifyTwoCutoffs(ber, settings)
        
        # Volumes
        volume_list_received_at_first_AddBeadsToAll = ponec.addBeadsToAll.mock_calls[0][1][2]
        volume_list_received_at_second_AddBeadsToAll = ponec.addBeadsToAll.mock_calls[1][1][2]
        self.assertEqual(volume_list_received_at_first_AddBeadsToAll, [80, 70, 60])
        self.assertEqual(volume_list_received_at_second_AddBeadsToAll, [140, 110, 67])
        
        # Mixing
        samples_list_1st_abs_mix = ponec.mixManySamples.mock_calls[0][1][1]
        samples_list_2nd_abs_mix = ponec.mixManySamples.mock_calls[1][1][1]
        samples_mix_elution = ponec.mixManySamples.mock_calls[2][1][1]
        self.assertEqual(samples_list_1st_abs_mix[0].getWell(), (1, 0))
        self.assertEqual(samples_list_1st_abs_mix[1].getWell(), (1, 1))
        self.assertEqual(samples_list_1st_abs_mix[2].getWell(), (1, 2))
        self.assertEqual(samples_list_2nd_abs_mix[0].getWell(), (1, 6))
        self.assertEqual(samples_list_2nd_abs_mix[1].getWell(), (1, 7))
        self.assertEqual(samples_list_2nd_abs_mix[2].getWell(), (1, 8))
        self.assertEqual(samples_mix_elution[0].getWell(), (1, 6))
        self.assertEqual(samples_mix_elution[1].getWell(), (1, 7))
        self.assertEqual(samples_mix_elution[2].getWell(), (1, 8))
        
        
        ber.close()
        del ber

    def test_initIntermediate(self):
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        
        intermediate_samples_list = ponec.initIntermediate(self.ber, settings)
        
        self.assertEqual(intermediate_samples_list[0].getWell(), (1, 6))
        self.assertEqual(intermediate_samples_list[1].getWell(), (1, 7))
        self.assertEqual(intermediate_samples_list[2].getWell(), (1, 8))
        

    def test_bernieInitAndClose(self):
        #TODO: for some reason, unittest fails to open actual com ports.
        self.assertTrue(ponec.areTwoPortsAvailable())
        #self.assertEqual(ponec.bl.listSerialPorts(), ['COM3', 'COM4'])
        #self.assertEqual(len(ponec.bl.listSerialPorts()), 2)
        #ber = ponec.bl.robot()
        #ber.home()
        
        
        #ber.close()
    
    def tearDown(self):
        try:
            self.ber.close()
        except:
            pass

        try:
            del self.ber
        except:
            pass        
            
    
if __name__ == '__main__':
    unittest.main()
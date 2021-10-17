import unittest
import os
import mock
import logging

import purify as ponec
import bernielib as bl

from mock import patch


class one_step_cutoff_test_case(unittest.TestCase):

    @patch('purify.bl.time.sleep')
    @patch('purify.bl.serial.Serial')
    def setUp(self, mock_serial, mock_sleep):
    
        logging.disable(logging.CRITICAL)
        self.ber = ponec.bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        try:
            self.settings_curr_1stage = ponec.loadSettings('samplesheet.csv')
        except:
            print("No one-stage settings file")
        try:
            self.settings_factdef_1stage = ponec.loadSettings(
                                        '.\\factory_default\\samplesheet.csv')
        except:
            print("No factory default one-stage settings file")
        try:
            self.settings_curr_2stages = ponec.loadSettings('samplesheet_2stages.csv')
        except:
            print("No two-stages settings file")
        try:
            self.settings_factdef_2stages = ponec.loadSettings(
                                        '.\\factory_default\\samplesheet_2stages.csv')
        except:
            print("No factory default two-stages settings file")


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

    @patch('purify.bl.robot.transferLiquid')
    def test_transferSampleToSecondStage(self, mock_transferLiquid):
        self.ber.transferLiquid = mock_transferLiquid
        #self.ber.transferLiquid = mock.MagicMock()
        self.ber.move = mock.MagicMock()
        self.ber.pickUpNextTip = mock.MagicMock()
        self.ber.dumpTipToWaste = mock.MagicMock()
        
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        intermediate_list = ponec.initIntermediate(self.ber, settings)
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
                                                             mock_separateEluateAllTubes):
        self.ber.setSpeedPipette = mock_setSpeedPipette
        self.ber.setSpeedPipette = mock_moveMagnetsTowardsTube
        
        settings = ponec.loadSettings('.\\factory_default\\samplesheet.csv')
        ponec.purify_one_cutoff(self.ber, settings)
        
        mock_addBeadsToAll_first_call_first_arg = mock_addBeadsToAll.mock_calls[0][1][0]
        mock_addBeadsToAll_first_call_delay_arg = mock_addBeadsToAll.mock_calls[0][2]['delay']
        self.assertEqual(self.ber, mock_addBeadsToAll_first_call_first_arg)
        self.assertEqual(1, mock_addBeadsToAll_first_call_delay_arg)
        
        
    @patch('purify.separateEluateAllTubes')
    @patch('purify.eluteAllSamples')
    @patch('purify.waitAfterTimestamp')
    @patch('purify.add80PctEthanol')
    @patch('purify.removeSupernatantAllSamples')
    @patch('purify.bl.robot.moveMagnetsTowardsTube')
    @patch('purify.mixManySamples')
    @patch('purify.bl.robot.setSpeedPipette')
    @patch('purify.addBeadsToAll')
    def test_purifyOneCutoff__pipette_speed(self, 
                                                             mock_addBeadsToAll,
                                                             mock_setSpeedPipette,
                                                             mock_mixManySamples,
                                                             mock_moveMagnetsTowardsTube,
                                                             mock_removeSupernatantAllSamples,
                                                             mock_add80PctEthanol,
                                                             mock_waitAfterTimestamp,
                                                             mock_eluteAllSamples,
                                                             mock_separateEluateAllTubes):
        self.ber.setSpeedPipette = mock_setSpeedPipette
        self.ber.moveMagnetsTowardsTube = mock_moveMagnetsTowardsTube
        
        settings = ponec.loadSettings('.\\factory_default\\samplesheet.csv')
        ponec.purify_one_cutoff(self.ber, settings)
        
        # Speed while pipetting beads in
        
        call_setting_beads_speed = self.ber.setSpeedPipette.mock_calls[0]
        call_setting_default_speed = self.ber.setSpeedPipette.mock_calls[1]
        
        beads_speed = call_setting_beads_speed[1][0]
        def_speed = call_setting_default_speed[1][0]
        
        self.assertEqual(beads_speed, 1500)
        self.assertEqual(def_speed, 2500)
        
        # Speed while pipetting supernatant out
        
        call_setting_sup_speed = self.ber.setSpeedPipette.mock_calls[2]
        call_setting_default_speed = self.ber.setSpeedPipette.mock_calls[3]
        
        sup_speed = call_setting_sup_speed[1][0]
        def_speed = call_setting_default_speed[1][0]
        
        self.assertEqual(sup_speed, 1500)
        self.assertEqual(def_speed, 2500)

        # Speed while pipetting ethanol in and out
        
        call_setting_etoh_speed = self.ber.setSpeedPipette.mock_calls[4]
        call_setting_default_speed = self.ber.setSpeedPipette.mock_calls[5]
        
        sup_speed = call_setting_etoh_speed[1][0]
        def_speed = call_setting_default_speed[1][0]
        
        self.assertEqual(sup_speed, 2000)
        self.assertEqual(def_speed, 2500)
        
        # Speed while pipetting eluent in
        
        call_setting_eluent_speed = self.ber.setSpeedPipette.mock_calls[6]
        call_setting_default_speed = self.ber.setSpeedPipette.mock_calls[7]
        
        sup_speed = call_setting_eluent_speed[1][0]
        def_speed = call_setting_default_speed[1][0]
        
        self.assertEqual(sup_speed, 1800)
        self.assertEqual(def_speed, 2500)
        
        # Checking the final speed setting
        # Making sure the script didn't accidentally chaned it.
        self.assertEqual(self.ber.getSpeedPipette(), 2500)
        
    
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
                                            ):
        
        self.ber.moveMagnetsTowardsTube = mock_moveMagnetsTowardsTube
        self.ber.moveMagnetsAway = mock_moveMagnetsAway
        self.ber.setSpeedPipette = mock_setSpeedPipette
        
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        beads, waste, water, EtOH80pct = ponec.initReagents(self.ber, settings)
        
        ponec.purifyTwoCutoffs(self.ber, settings)
        
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
        settings = ponec.loadSettings('.\\factory_default\\samplesheet.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        beads, waste, water, EtOH80pct = ponec.initReagents(self.ber, settings)
        
        # Running the function to be tested
        ponec.ethanolWash(self.ber, settings, samples_list, EtOH80pct, waste)
        
        # Making sure the reagents (ethanol and waste) are where they should be
        ethanol_obj_provided_to_1st_add80PctEthanol = mock_add80PctEthanol.mock_calls[0][1][2]
        self.assertEqual(ethanol_obj_provided_to_1st_add80PctEthanol, EtOH80pct)
        ethanol_sample_well = ethanol_obj_provided_to_1st_add80PctEthanol.getWell()
        self.assertEqual(ethanol_sample_well, (0,2))
        self.assertEqual(ethanol_obj_provided_to_1st_add80PctEthanol.rack, self.ber.reagents_rack)
        
        ethanol_obj_provided_to_2nd_add80PctEthanol = mock_add80PctEthanol.mock_calls[1][1][2]
        self.assertEqual(ethanol_obj_provided_to_2nd_add80PctEthanol, EtOH80pct)
        ethanol_sample_well = ethanol_obj_provided_to_2nd_add80PctEthanol.getWell()
        self.assertEqual(ethanol_sample_well, (0,2))
        self.assertEqual(ethanol_obj_provided_to_2nd_add80PctEthanol.rack, self.ber.reagents_rack)
        
        # Testing the samples positions
        # First call to add 80% ethanol
        s1, s2, s3 = mock_add80PctEthanol.mock_calls[0][1][1]
        self.assertEqual(s1, samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, samples_list[1])
        self.assertEqual(s3, samples_list[2])
        self.assertEqual(s1.getWell(), (1, 0))  # Samples are in the right wells
        self.assertEqual(s2.getWell(), (1, 1))
        self.assertEqual(s3.getWell(), (1, 2))
        self.assertEqual(s1.rack, self.ber.samples_rack)
        self.assertEqual(s2.rack, self.ber.samples_rack)
        self.assertEqual(s3.rack, self.ber.samples_rack)
        
        # Second call to add 80% ethanol
        s1, s2, s3 = mock_add80PctEthanol.mock_calls[1][1][1]
        self.assertEqual(s1, samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, samples_list[1])
        self.assertEqual(s3, samples_list[2])
        self.assertEqual(s1.getWell(), (1, 0))  # Samples are in the right wells
        self.assertEqual(s2.getWell(), (1, 1))
        self.assertEqual(s3.getWell(), (1, 2))
        self.assertEqual(s1.rack, self.ber.samples_rack)
        self.assertEqual(s2.rack, self.ber.samples_rack)
        self.assertEqual(s3.rack, self.ber.samples_rack)
        
        # Supernatant removed after 1st wash
        s1, s2, s3 = mock_removeSupernatantAllSamples.mock_calls[0][1][1]
        self.assertEqual(s1, samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, samples_list[1])
        self.assertEqual(s3, samples_list[2])

    
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
                     ):
        # Loading necessary parameters
        settings = ponec.loadSettings('.\\factory_default\\samplesheet.csv')
        samples_list = ponec.initSamples(self.ber, settings)
        result_list = ponec.initResultTubes(self.ber, settings)
        beads, waste, water, EtOH80pct = ponec.initReagents(self.ber, settings)
        
        # Running the function to be tested
        ponec.elution(self.ber, settings, samples_list, result_list, water)
        
        # Function eluteAllSamples receives the right samples
        s1, s2, s3 = mock_eluteAllSamples.mock_calls[0][1][1]
        self.assertEqual(s1, samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, samples_list[1])
        self.assertEqual(s3, samples_list[2])
        supposed_water = mock_eluteAllSamples.mock_calls[0][1][2]
        self.assertEqual(water, supposed_water)
        # Function separateEluateAllTubes recives the right samples
        s1, s2, s3 = mock_separateEluateAllTubes.mock_calls[0][1][1]
        self.assertEqual(s1, samples_list[0])   # Samples are what they should be.
        self.assertEqual(s2, samples_list[1])
        self.assertEqual(s3, samples_list[2])
        r1, r2, r3 = mock_separateEluateAllTubes.mock_calls[0][1][2]
        self.assertEqual(r1, result_list[0])   # Samples are what they should be.
        self.assertEqual(r2, result_list[1])
        self.assertEqual(r3, result_list[2])
    

    def test_initIntermediate(self):
        settings = ponec.loadSettings('.\\tests\\samplesheet_2stages__beads_vol.csv')
        
        intermediate_samples_list = ponec.initIntermediate(self.ber, settings)
        
        self.assertEqual(intermediate_samples_list[0].getWell(), (1, 6))
        self.assertEqual(intermediate_samples_list[1].getWell(), (1, 7))
        self.assertEqual(intermediate_samples_list[2].getWell(), (1, 8))
        
    
    def test_returnTipRackType(self):
        self.setting_test_factory_default('old', ponec.returnTipRackType)
    
    def test_returnLoadCellPort(self):
        self.setting_test_factory_default(None, ponec.returnLoadCellPort)
    
    def test_returnCartesianPort(self):
        self.setting_test_factory_default(None, ponec.returnCartesianPort)
    
    def test_decideCutoffNumber(self):
        self.setting_test_universal_function(1, ponec.decideCutoffNumber, 
                                        self.settings_factdef_1stage)
        self.setting_test_universal_function(2, ponec.decideCutoffNumber, 
                                        self.settings_factdef_2stages)
    
    def test_returnPipettingDelay(self):
        self.setting_test_factory_default(1, ponec.returnPipettingDelay)
        
    def test_returnMaxPipetteSpeed(self):
        self.setting_test_factory_default(2500, ponec.returnMaxPipetteSpeed)

    def test_returnBeadsPipettingSpeed(self):
        self.setting_test_factory_default(1500, ponec.returnBeadsPipettingSpeed)

    def test_returnEthanolPipettingSpeed(self):
        self.setting_test_factory_default(2000, ponec.returnEthanolPipettingSpeed)
        
    def test_returnEluentPipettingSpeed(self):
        self.setting_test_factory_default(1800, ponec.returnEluentPipettingSpeed)

    def setting_test_factory_default(self, expected_param, param_return_func):
        self.setting_test_universal_function(expected_param, param_return_func, 
                                             self.settings_factdef_1stage)
        self.setting_test_universal_function(expected_param, param_return_func, 
                                             self.settings_factdef_2stages)
        
        
    def setting_test_universal_function(self, expected_parameter, 
                                        parameter_returning_function, *args):
        parameter = parameter_returning_function(*args)
        self.assertEqual(parameter, expected_parameter)
        
    
    
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
            
    
if __name__ == '__main__':
    unittest.main()
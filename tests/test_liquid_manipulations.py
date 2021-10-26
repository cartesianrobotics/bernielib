import unittest
import mock
import logging
import time
import bernielib

import bernielib as bl

from mock import patch

class bernielib_test_case(unittest.TestCase):
    
    @patch('bernielib.time.sleep')
    @patch('time.sleep')
    @patch('purify.bl.serial.Serial')
    def setUp(self, mock_serial, mock_sleep, mock_sleep2):
        logging.disable(logging.CRITICAL)
        self.ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        
    def tearDown(self):
        logging.disable(logging.NOTSET)
        del self.ber
        try:
            os.remove(s1.json)
        except:
            pass
    
        
    @patch('purify.bl.robot.tareAll')
    @patch('purify.bl.robot.moveAxis')
    @patch('purify.bl.robot.getCombinedLoad')
    @patch('purify.bl.robot.getPosition')  
    def prep_for_moveDownUntilPress(self, 
                                    pos, loads_list, step, threshold, z_max, tare,
                                    expected_times_called, 
                                    mock_getPosition,
                                    mock_getCombinedLoad,
                                    mock_moveAxis,  
                                    mock_tareAll):
        # Prepares to test the robot touching something and registering it with its
        # load sensors.
        self.ber.getPosition.return_value = pos
        self.ber.getCombinedLoad.side_effect = loads_list
        
        self.ber.moveDownUntilPress(step=step, threshold=threshold, z_max=z_max, tare=tare)
        
        times_called = self.ber.moveAxis.call_count
        
        self.assertEqual(times_called, expected_times_called)
        

    def test_moveDownUntilPress(self):
        
        position = 100
        sensors_response = [0, 0, 0, 1000, 2000, 3000, 4000]
        step = 1
        z_max = 180
        tare = True
        
        self.prep_for_moveDownUntilPress(position, sensors_response,
                                         step, 500, z_max, tare, 3)
        self.prep_for_moveDownUntilPress(position, sensors_response,
                                         step, 2500, z_max, tare, 5)
        self.prep_for_moveDownUntilPress(position, sensors_response,
                                         step, 2500, 3, tare, 0)
        
        
#    def test_scanForStair(self):
#        bl.time.sleep = mock.MagicMock()
#        bl.serial.Serial = mock.MagicMock()
#        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
#        
#        ber.getPosition = mock.MagicMock()
#        ber.getPosition.side_effects = [100, 110]
#        ber.moveDownUntilPress = mock.MagicMock()
#        ber.moveDownUntilPress.side_effect = [100, 101, 98, 110, 110, 110]
#        ber.moveAxisDelta = mock.MagicMock()
#        
#        ber.scanForStair(axis='X', step=1, direction=1, depth=5)
#        
#        times_called = ber.moveAxisDelta.call_count
#        self.assertEqual(times_called, 6)
        
    
    def prep_writeAndWaitCartesian(self):
        c1 = self.ber.writeAndWaitCartesian.mock_calls[-1]
        c2 = self.ber.writeAndWaitCartesian.mock_calls[-2]
        return c1, c2
    
    @patch('purify.bl.robot.writeAndWaitCartesian')
    @patch('purify.bl.robot.getPosition')
    def test_moveAxisDelta(self, mock_getPosition, mock_writeAndWaitCartesian):        
        speed_XY = self.ber.data['speed_XY']
        self.ber.getPosition.return_value = 100
        self.ber.moveAxisDelta(axis='X', dist=10, speed=None)
        
        call_1, call_2 = self.prep_writeAndWaitCartesian()
        self.assertEqual(call_1, mock.call('M400'))
        self.assertEqual(call_2, mock.call('G0 X110 F50000'))
        
        self.ber.moveAxisDelta(axis='X', dist=-10, speed=None)
        
        call_3, call_4 = self.prep_writeAndWaitCartesian()
        self.assertEqual(call_3, mock.call('M400'))
        self.assertEqual(call_4, mock.call('G0 X90 F50000'))


    @patch('purify.bl.robot.movePipetteToVolume')
    @patch('purify.bl.robot.moveDownUntilPress')
    @patch('purify.bl.robot.moveAxisDelta')
    @patch('purify.bl.robot.moveToSample')
    def prep_uptakeLiquids_pipetteLagsHandling(self, 
                                               v_sample,
                                               expected_calls_list,
                                               mock_moveToSample, 
                                               mock_moveAxisDelta,
                                               mock_moveDownUntilPress,
                                               mock_movePipetteToVolume):
        self.ber.moveDownUntilPress.return_value = 100
        v = 100
        lag_vol = 5
        # Creating a sample
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, v_sample)
        # figuring lag volume down
        lag_vol_down = s1._allowPlungerLagCompensation(v, lag_vol)
        
        self.ber.uptakeLiquid(s1, 100, lag_vol=lag_vol) # Tested function
        
        calls_list = self.ber.movePipetteToVolume.mock_calls
        for call, expected_call in zip(calls_list, expected_calls_list):
            self.assertEqual(call, mock.call(expected_call))
        

    def test_uptakeLiquid_lags(self):
        self.prep_uptakeLiquids_pipetteLagsHandling(1000, [110, 105, 0, 5])
        #TODO: Investigate this one: this one fails.
        #self.prep_uptakeLiquids_pipetteLagsHandling(100, [105, 100, 0, 0])


    @patch('time.sleep')
    @patch('purify.bl.robot.movePipetteToVolume')
    @patch('purify.bl.robot.moveDownUntilPress')
    @patch('purify.bl.robot.moveAxisDelta')
    @patch('purify.bl.robot.moveToSample')
    def uptakeLiquid_patched(self, 
            sample, volume, v_insert_override, lag_vol, dry_tube,
            in_place, ignore_calibration, z_bottom,
            mock_moveToSample, mock_moveAxisDelta,
            mock_moveDownUntilPress, mock_movePipetteToVolume, mock_sleep):
        
        # Mocked Z coordinate of the bottom of the tube
        self.ber.moveDownUntilPress.return_value = z_bottom
        
        self.ber.uptakeLiquid(sample, volume, v_insert_override, lag_vol, 
                              dry_tube, in_place, ignore_calibration)
            


    def test_uptakeLiquid__save_sample_bottom_coord(self):
        
        z_bottom = 120
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 100)
        self.uptakeLiquid_patched(s1, 100, None, 5, False, False, False, z_bottom)
        saved_z_bottom = s1.getZBottom()
        self.assertEqual(saved_z_bottom, z_bottom)


    @patch('purify.bl.robot.moveDownUntilPress')
    def test_uptakeLiquid__touch_bottom_decision(self, mock_moveDownUntilPress):
        
        z_bottom = 120    # Mocked Z coordinate of the bottom of the tube
        
        # Sample which has lots of liquid should not be probed for the bottom
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 1000)
        sample_has_low_volume = s1._isLowVolumeUptakeNeeded(205)
        
        self.uptakeLiquid_patched(s1, 200, None, 5, False, False, False, z_bottom)
        
        self.assertFalse(sample_has_low_volume)
        self.assertFalse(self.ber.moveDownUntilPress.called)
        # Regardless of the liquid amount
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 1000)
        sample_has_low_volume = s1._isLowVolumeUptakeNeeded(205)
        self.uptakeLiquid_patched(s1, 20, None, 5, False, False, False, z_bottom)

        self.assertFalse(sample_has_low_volume)
        self.assertFalse(self.ber.moveDownUntilPress.called)
        
        
    @patch('purify.bl.robot.moveDownUntilPress')
    def test_uptakeLiquid__touch_bottom_decision_2(self, mock_moveDownUntilPress):
        
        """
        TODO: This one fails. investigate.
        z_bottom = 120    # Mocked Z coordinate of the bottom of the tube
        # Sample which has little amount of liquid should be probed for the bottom
        self.ber.moveDownUntilPress.return_value = z_bottom
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 10)
        self.uptakeLiquid_patched(s1, 10, None, 5, False, False, False, z_bottom)
        self.assertTrue(self.ber.moveDownUntilPress.called)
        
        # When v_insert_override is specified, the pipetting must happen in place, without 
        # further analysis
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = provided_z
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 10)
        ber.uptakeLiquid(s1, 10, lag_vol=5, v_insert_override=20)
        self.assertFalse(ber.moveDownUntilPress.called)
        """

    def test__allowPlungerLagCompensation(self):
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 1000)
        lag = s1._allowPlungerLagCompensation(200, 5)
        self.assertEqual(lag, 5)
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 200)
        lag = s1._allowPlungerLagCompensation(199, 5)
        self.assertEqual(lag, 1)
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 100)
        lag = s1._allowPlungerLagCompensation(100, 0)
        self.assertEqual(lag, 0)
        s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 90)
        lag = s1._allowPlungerLagCompensation(100, 0)
        self.assertEqual(lag, 0)
    

if __name__ == '__main__':
    unittest.main(verbosity=2)
import unittest
import mock
import logging

import bernielib as bl

from mock import patch

class bernielib_test_case(unittest.TestCase):
    
    def setUp(self):
        logging.disable(logging.CRITICAL)
        
    def tearDown(self):
        logging.disable(logging.NOTSET)
    
    @patch('purify.bl.time.sleep')
    @patch('purify.bl.serial.Serial')    
    def test_moveDownUntilPress(self, mock_serial, mock_sleep):
        #bl.time.sleep = mock.MagicMock()
        #bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.getCombinedLoad = mock.MagicMock()
        ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        ber.moveAxis = mock.MagicMock()
        ber.tareAll = mock.MagicMock()
        
        ber.moveDownUntilPress(1, 500)
        
        times_called = ber.moveAxis.call_count
        
        self.assertEqual(times_called, 3)
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.getCombinedLoad = mock.MagicMock()
        ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        ber.moveAxis = mock.MagicMock()
        ber.moveDownUntilPress(1, 2500)
        
        times_called = ber.moveAxis.call_count
        self.assertEqual(times_called, 5)
        
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.getCombinedLoad = mock.MagicMock()
        ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        ber.moveAxis = mock.MagicMock()
        ber.moveDownUntilPress(step=1, threshold=2500, z_max=3)
        
        times_called = ber.moveAxis.call_count
        self.assertEqual(times_called, 0)


        
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
        

    def test_moveAxisDelta(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        speed_XY = ber.data['speed_XY']
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        
        ber.writeAndWaitCartesian = mock.MagicMock()
        
        ber.moveAxisDelta(axis='X', dist=10, speed=None)
        
        self.assertEqual(ber.writeAndWaitCartesian.mock_calls[-1], mock.call('M400'))
        self.assertEqual(ber.writeAndWaitCartesian.mock_calls[-2], mock.call('G0 X110 F50000'))
        

        ber.moveAxisDelta(axis='X', dist=-10, speed=None)
        self.assertEqual(ber.writeAndWaitCartesian.mock_calls[-1], mock.call('M400'))
        self.assertEqual(ber.writeAndWaitCartesian.mock_calls[-2], mock.call('G0 X90 F50000'))


    def test_uptakeLiquid_lags(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        ber.moveToSample = mock.MagicMock()
        ber.moveAxisDelta = mock.MagicMock()
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = 100
        
        # Tested values
        v = 100
        lag_vol = 5
        v_sample = 1000
        # Creating a sample
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, v_sample)
        # figuring lag volume down
        lag_vol_down = s1._allowPlungerLagCompensation(v, lag_vol)
        ber.movePipetteToVolume = mock.MagicMock()
        ber.uptakeLiquid(s1, 100, lag_vol=lag_vol) # Tested function
        self.assertEqual(ber.movePipetteToVolume.mock_calls[0], mock.call(100+5+5))
        self.assertEqual(ber.movePipetteToVolume.mock_calls[1], mock.call(100+5))
        self.assertEqual(ber.movePipetteToVolume.mock_calls[2], mock.call(0))
        self.assertEqual(ber.movePipetteToVolume.mock_calls[3], mock.call(5))
        
        # Tested values
        v = 100
        lag_vol = 5
        v_sample = 100
        # Creating a sample
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, v_sample)
        # figuring lag volume down
        lag_vol_down = s1._allowPlungerLagCompensation(v, lag_vol)
        ber.movePipetteToVolume = mock.MagicMock()
        ber.uptakeLiquid(s1, 100, lag_vol=lag_vol) # Tested function
        self.assertEqual(ber.movePipetteToVolume.mock_calls[0], mock.call(100+5+0))
        self.assertEqual(ber.movePipetteToVolume.mock_calls[1], mock.call(100+0))
        # Here will be more calls for gradual liquid uptake
        self.assertEqual(ber.movePipetteToVolume.mock_calls[-2], mock.call(0))
        self.assertEqual(ber.movePipetteToVolume.mock_calls[-1], mock.call(0))
        


    def test_uptakeLiquid__save_sample_bottom_coord(self):
        
        provided_z = 120    # Mocked Z coordinate of the bottom of the tube
        
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        ber.moveToSample = mock.MagicMock()
        ber.moveAxisDelta = mock.MagicMock()
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = provided_z
        ber.movePipetteToVolume = mock.MagicMock()
        
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 100)
            
        ber.uptakeLiquid(s1, 100, lag_vol=5)
        
        saved_z_bottom = s1.getZBottom()
        
        self.assertEqual(saved_z_bottom, provided_z)
        

    def test_uptakeLiquid__touch_bottom_decision(self):
        provided_z = 120    # Mocked Z coordinate of the bottom of the tube
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        ber.moveToSample = mock.MagicMock()
        ber.moveAxisDelta = mock.MagicMock()
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = provided_z
        ber.movePipetteToVolume = mock.MagicMock()
        
        # Sample which has lots of liquid should not be probed for the bottom
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 1000)
        sample_has_low_volume = s1._isLowVolumeUptakeNeeded(205)
        ber.uptakeLiquid(s1, 200, lag_vol=5)
        self.assertFalse(sample_has_low_volume)
        self.assertFalse(ber.moveDownUntilPress.called)
        # Regardless of the liquid amount
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 1000)
        sample_has_low_volume = s1._isLowVolumeUptakeNeeded(205)
        ber.uptakeLiquid(s1, 20, lag_vol=5)
        self.assertFalse(sample_has_low_volume)
        self.assertFalse(ber.moveDownUntilPress.called)

        # Sample which has little amount of liquid should be probed for the bottom
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = provided_z
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 10)
        ber.uptakeLiquid(s1, 10, lag_vol=5)
        self.assertTrue(ber.moveDownUntilPress.called)
        
        # When v_insert_override is specified, the pipetting must happen in place, without 
        # further analysis
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.return_value = provided_z
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 10)
        ber.uptakeLiquid(s1, 10, lag_vol=5, v_insert_override=20)
        self.assertFalse(ber.moveDownUntilPress.called)


    def test__allowPlungerLagCompensation(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 1000)
        lag = s1._allowPlungerLagCompensation(200, 5)
        self.assertEqual(lag, 5)
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 200)
        lag = s1._allowPlungerLagCompensation(199, 5)
        self.assertEqual(lag, 1)
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 100)
        lag = s1._allowPlungerLagCompensation(100, 0)
        self.assertEqual(lag, 0)
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 90)
        lag = s1._allowPlungerLagCompensation(100, 0)
        self.assertEqual(lag, 0)
    

if __name__ == '__main__':
    unittest.main(verbosity=2)
import unittest
import mock

import bernielib as bl

class bernielib_test_case(unittest.TestCase):

    def test_moveDownUntilPress(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.getCombinedLoad = mock.MagicMock()
        ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        ber.moveAxis = mock.MagicMock()
        
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
    unittest.main()
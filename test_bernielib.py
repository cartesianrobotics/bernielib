import unittest
import mock

import bernielib as bl


class bernielib_test_case(unittest.TestCase):

    def test_moveDownUntilPress(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM18', pipette_port_name='COM7', misc_port_name='COM20')
        
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
        ber.moveDownUntilPress(1, 2500, 3)
        
        times_called = ber.moveAxis.call_count
        self.assertEqual(times_called, 3)
        
        
    def test_scanForStair(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM18', pipette_port_name='COM7', misc_port_name='COM20')
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.side_effect = [100, 101, 98, 110, 110, 110]
        ber.moveAxisDelta = mock.MagicMock()
        
        ber.scanForStair(axis='X', step=1, direction=1, z_increment=1, z_max_travel=4, z_threshold=500)
        
        times_called = ber.moveAxisDelta.call_count
        self.assertEqual(times_called, 6)
        

    def test_moveAxisDelta(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM18', pipette_port_name='COM7', misc_port_name='COM20')
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        
        ber.writeAndWaitCartesian = mock.MagicMock()
        
        ber.moveAxisDelta(axis='X', dist=10, speed=None)
        
        ber.writeAndWaitCartesian.assert_called_with("G0 X110 F6000")
        
        ber.moveAxisDelta(axis='X', dist=-10, speed=None)
    
        ber.writeAndWaitCartesian.assert_called_with("G0 X90 F6000")


if __name__ == '__main__':
    unittest.main()
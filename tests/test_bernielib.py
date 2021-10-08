import unittest
import mock
import time
import logging

import bernielib as bl


class bernielib_test_case(unittest.TestCase):
    
    def setUp(self):
        
        self.tearDown()
        
        logging.disable(logging.CRITICAL)
        
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        self.ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')
    
    def test_moveDownUntilPress(self):
        self.ber.getPosition = mock.MagicMock()
        self.ber.getPosition.return_value = 100
        self.ber.getCombinedLoad = mock.MagicMock()
        self.ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        self.ber.moveAxis = mock.MagicMock()
        self.ber.tareAll = mock.MagicMock()
        
        self.ber.moveDownUntilPress(1, 500)

        times_called = self.ber.moveAxis.call_count
        
        self.assertEqual(times_called, 3)
        
        self.ber.getPosition = mock.MagicMock()
        self.ber.getPosition.return_value = 100
        self.ber.getCombinedLoad = mock.MagicMock()
        self.ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        self.ber.moveAxis = mock.MagicMock()
        self.ber.moveDownUntilPress(1, 2500)
        
        times_called = self.ber.moveAxis.call_count
        self.assertEqual(times_called, 5)
        
        # This tests overshooting maximum allowed Z coordinate (robot went too deep)
        # At this condition, should not execute moveAxis
        self.ber.getPosition = mock.MagicMock()
        self.ber.getPosition.return_value = 100
        self.ber.getCombinedLoad = mock.MagicMock()
        self.ber.getCombinedLoad.side_effect = [0, 0, 0, 1000, 2000, 3000, 4000]
        self.ber.moveAxis = mock.MagicMock()
        self.ber.moveDownUntilPress(1, 2500, z_max=90)
        
        times_called = self.ber.moveAxis.call_count
        self.assertEqual(times_called, 0)

        
    """        
    def test_scanForStair(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')
        
        ber.getPosition = mock.MagicMock()
        ber.getPosition.return_value = 100
        ber.moveDownUntilPress = mock.MagicMock()
        ber.moveDownUntilPress.side_effect = [100, 101, 98, 110, 110, 110]
        ber.moveAxisDelta = mock.MagicMock()
        
        ber.scanForStair(axis='X', step=1, direction=1, depth=5)
        
        times_called = ber.moveAxisDelta.call_count
        self.assertEqual(times_called, 6)
    """        

    def test_moveAxisDelta(self):        
        self.ber.getPosition = mock.MagicMock()
        self.ber.getPosition.return_value = 100
        
        self.ber.writeAndWaitCartesian = mock.MagicMock()
        
        
        self.ber.moveAxisDelta(axis='X', dist=10, speed=None)
        
        first_call = self.ber.writeAndWaitCartesian.mock_calls[0][1][0]
        self.assertEqual(first_call, "G0 X110 F50000")
        
        self.ber.moveAxisDelta(axis='X', dist=-10, speed=None)
        second_call = self.ber.writeAndWaitCartesian.mock_calls[2][1][0]
        self.assertEqual(second_call, "G0 X90 F50000")


    def test__readUntilMatch_ProperMessage(self):
        port = self.ber.loadcell_port
        expected_pattern = 'ok\n'
        timeout = 0.5
        
        # Testing whether the function be able to read an entire message
        self.ber._readAll = mock.MagicMock()
        self.ber._readAll.side_effect = ['', '', '', 'asdf', 'fdsa', 'ok\n']
        
        msg = self.ber._readUntilMatch(port=port, pattern=expected_pattern, timeout=timeout)
        
        self.assertEqual(msg, 'asdffdsaok\n')
        

    def test__readUntilMatch_NeverReceiveConfirmation(self):
        port = self.ber.loadcell_port
        expected_pattern = 'ok\n'
        timeout = 0.5
        
        # Testing whether the function be able to read an entire message
        self.ber._readAll = mock.MagicMock()
        self.ber._readAll.return_value = 'a'
        
        before_ts = time.time()
        msg = self.ber._readUntilMatch(port=port, pattern=expected_pattern, timeout=timeout)
        after_ts = time.time()
        waited_before_timeout = after_ts - before_ts
        
        self.assertIsNone(msg)
        self.assertTrue(waited_before_timeout >= timeout)
        


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
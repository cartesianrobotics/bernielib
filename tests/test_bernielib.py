import unittest
import mock

import time
import logging

import bernielib as bl


from mock import patch

class bernielib_test_case(unittest.TestCase):
    
    @patch('time.sleep')
    @patch('serial.Serial')
    def setUp(self, mock_serial, mock_sleep):
        
        self.tearDown()
        logging.disable(logging.CRITICAL)
        self.ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')
    
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


    @patch('purify.bl.robot.tareAll')
    @patch('purify.bl.robot.moveAxis')
    @patch('purify.bl.robot.getCombinedLoad', side_effect=[0, 0, 0, 1000, 2000, 3000, 4000])
    @patch('purify.bl.robot.getPosition', return_value=100)
    def test_moveDownUntilPress(self, mock_getPosition, mock_getCombinedLoad,
            mock_moveAxis, mock_tareAll):
        
        self.ber.moveDownUntilPress(1, 500)

        times_called = self.ber.moveAxis.call_count
        
        self.assertEqual(times_called, 3)

    
    @patch('purify.bl.robot.tareAll')
    @patch('purify.bl.robot.moveAxis')
    @patch('purify.bl.robot.getCombinedLoad', side_effect=[0, 0, 0, 1000, 2000, 3000, 4000])
    @patch('purify.bl.robot.getPosition', return_value=100)
    def test_moveDownUntilPress2(self, mock_getPosition, mock_getCombinedLoad,
            mock_moveAxis, mock_tareAll):
        
        self.ber.moveDownUntilPress(1, 2500, z_max=90)

        times_called = self.ber.moveAxis.call_count
        
        self.assertEqual(times_called, 0)
    
    
    @patch('purify.bl.robot.tareAll')
    @patch('purify.bl.robot.moveAxis')
    @patch('purify.bl.robot.getCombinedLoad', side_effect=[0, 0, 0, 1000, 2000, 3000, 4000])
    @patch('purify.bl.robot.getPosition', return_value=100)
    def test_moveDownUntilPress(self, mock_getPosition, mock_getCombinedLoad,
            mock_moveAxis, mock_tareAll):
        
        self.ber.moveDownUntilPress(1, 500)

        times_called = self.ber.moveAxis.call_count
        
        self.assertEqual(times_called, 3)
        
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

    
    @patch('purify.bl.robot.writeAndWaitCartesian')
    @patch('purify.bl.robot.getPosition', return_value=100)
    def test_moveAxisDelta(self, mock_getPosition, mock_writeAndWaitCartesian):        
        self.ber.moveAxisDelta(axis='X', dist=10, speed=None)
        
        first_call = self.ber.writeAndWaitCartesian.mock_calls[0][1][0]
        self.assertEqual(first_call, "G0 X110 F50000")
        
        self.ber.moveAxisDelta(axis='X', dist=-10, speed=None)
        second_call = self.ber.writeAndWaitCartesian.mock_calls[2][1][0]
        self.assertEqual(second_call, "G0 X90 F50000")


    @patch('purify.bl.robot._readAll', side_effect=['', '', '', 'asdf', 'fdsa', 'ok\n'])
    def test__readUntilMatch_ProperMessage(self, mock_readAll):
        port = self.ber.loadcell_port
        expected_pattern = 'ok\n'
        timeout = 0.5
        # Testing whether the function be able to read an entire message        
        msg = self.ber._readUntilMatch(port=port, pattern=expected_pattern, timeout=timeout)
        self.assertEqual(msg, 'asdffdsaok\n')
        

    @patch('purify.bl.robot._readAll', return_value='a')
    def test__readUntilMatch_NeverReceiveConfirmation(self, mock_readAll):
        port = self.ber.loadcell_port
        expected_pattern = 'ok\n'
        timeout = 0.5
        
        # Testing whether the function be able to read an entire message        
        before_ts = time.time()
        msg = self.ber._readUntilMatch(port=port, pattern=expected_pattern, timeout=timeout)
        after_ts = time.time()
        waited_before_timeout = after_ts - before_ts
        
        self.assertIsNone(msg)
        self.assertTrue(waited_before_timeout >= timeout)
        

    def test__getBeadsVolumeCoef(self):
        a, b, c = bl.getBeadsVolumeCoef()
        # Coefficients are not None
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertIsNotNone(c)
        # Coefficients are of the right type
        self.assertIsInstance(a, float)
        self.assertIsInstance(b, float)
        self.assertIsInstance(c, float)

        


if __name__ == '__main__':
    unittest.main()
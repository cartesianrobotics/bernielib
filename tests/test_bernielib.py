import unittest

import time
import logging

import bernielib as bl


from unittest.mock import MagicMock, patch, call

class bernielib_test_case(unittest.TestCase):
    
    def setUp(self):
        logging.disable(logging.CRITICAL)
        # NOTE: a @patch decorator on setUp is undone before the test body
        # starts, so the serial port used to be unmocked during the tests
        # themselves. The patcher is started here and stopped through
        # addCleanup, which keeps it in place for the test and for tearDown.
        serial_patcher = patch('serial.Serial')
        serial_patcher.start()
        self.addCleanup(serial_patcher.stop)
        # time is mocked only while the fixture is built, which is exactly the
        # scope the original decorator had. Extending it over the test body
        # would break the tests here that measure a real timeout.
        with patch('time.sleep'):
            self.ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')
    
    def tearDown(self):
        # setUp used to call this method before it had built anything, which is
        # why the two statements below were wrapped in bare try/except. unittest
        # builds a fresh instance per test and only calls tearDown when setUp
        # succeeded, so self.ber is always there.
        self.ber.close()
        del self.ber
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


    def test_moveCoordinated_sends_all_axes_in_one_g1_block(self):
        with patch.object(self.ber, 'writeAndWaitCartesian') as write, \
                patch.object(self.ber, 'powerStepperOff') as power_off:
            self.ber.moveCoordinated(x=1, y=2, z=3, a=4, speed=600)

        self.assertEqual(write.call_args_list, [
            call('G1 X1 Y2 Z3 A4 F600'),
            call('M400'),
        ])
        power_off.assert_called_once_with('A')


    def test_moveCoordinated_queues_waypoints_until_final_wait(self):
        waypoints = [
            {'x': 160.87, 'z': 123.0, 'a': 1.272, 'wait': False},
            {'x': 160.87, 'z': 127.0, 'a': 2.199, 'wait': False},
            {'x': 160.241, 'z': 131.0, 'a': 3.125, 'wait': False},
            {'x': 159.612, 'z': 135.0, 'a': 4.052},
        ]

        with patch.object(self.ber, 'writeAndWaitCartesian') as write, \
                patch.object(self.ber, 'powerStepperOff') as power_off:
            for waypoint in waypoints:
                self.ber.moveCoordinated(speed=600, **waypoint)

        self.assertEqual(write.call_args_list, [
            call('G1 X160.87 Z123.0 A1.272 F600'),
            call('G1 X160.87 Z127.0 A2.199 F600'),
            call('G1 X160.241 Z131.0 A3.125 F600'),
            call('G1 X159.612 Z135.0 A4.052 F600'),
            call('M400'),
        ])
        power_off.assert_called_once_with('A')


    def test_moveCoordinated_without_a_does_not_power_off_pipette(self):
        with patch.object(self.ber, 'writeAndWaitCartesian') as write, \
                patch.object(self.ber, 'powerStepperOff') as power_off:
            self.ber.moveCoordinated(x=10, z=20, speed=300)

        self.assertEqual(write.call_args_list, [
            call('G1 X10 Z20 F300'),
            call('M400'),
        ])
        power_off.assert_not_called()


    def test_moveCoordinated_uses_slowest_configured_axis_speed(self):
        with patch.object(self.ber, 'writeAndWaitCartesian') as write, \
                patch.object(self.ber, 'powerStepperOff'):
            self.ber.moveCoordinated(x=10, z=20, a=3)

        self.assertEqual(write.call_args_list[0], call('G1 X10 Z20 A3 F2500'))


    def test_moveCoordinated_rejects_invalid_commands_before_writing(self):
        with patch.object(self.ber, 'writeAndWaitCartesian') as write:
            with self.assertRaises(ValueError):
                self.ber.moveCoordinated(speed=600)
            with self.assertRaises(ValueError):
                self.ber.moveCoordinated(x=float('nan'), speed=600)
            with self.assertRaises(ValueError):
                self.ber.moveCoordinated(x=1, speed=0)

        write.assert_not_called()


    def test_uptakeLiquidSinglePosition_uses_one_stroke_at_calibrated_bottom(self):
        sample = MagicMock()
        sample.getVolume.return_value = 30
        sample._settingPresent.return_value = True
        sample.getZBottom.return_value = 135.625
        sample.stype.getLowVolTipBottomGap.return_value = 0.15
        events = []

        with patch.object(self.ber, 'movePipetteToVolume',
                          side_effect=lambda volume: events.append(('plunger', volume))), \
                patch.object(self.ber, 'moveToSample',
                             side_effect=lambda sample, z: events.append(('position', z))), \
                patch.object(self.ber, '_probeTubeZBottom') as probe, \
                patch('bernielib.time.sleep'):
            self.ber.uptakeLiquidSinglePosition(sample, 20)

        self.assertEqual(events, [
            ('plunger', 20),
            ('position', 135.475),
            ('plunger', 0),
        ])
        probe.assert_not_called()
        sample.setVolume.assert_called_once_with(10.0)


    def test_uptakeLiquidSinglePosition_probes_once_before_first_stroke(self):
        sample = MagicMock()
        sample.getVolume.return_value = 30
        sample._settingPresent.return_value = False
        sample.stype.getLowVolTipBottomGap.return_value = 0.15
        events = []

        with patch.object(self.ber, 'movePipetteToVolume',
                          side_effect=lambda volume: events.append(('plunger', volume))), \
                patch.object(self.ber, '_probeTubeZBottom',
                             side_effect=lambda sample: (events.append(('probe',)) or 135.625)), \
                patch.object(self.ber, 'moveAxis',
                             side_effect=lambda axis, z: events.append(('lift', axis, z))), \
                patch.object(self.ber, 'moveToSample') as move_to_sample, \
                patch('bernielib.time.sleep'):
            self.ber.uptakeLiquidSinglePosition(sample, 20)

        self.assertEqual(events, [
            ('plunger', 20),
            ('probe',),
            ('lift', 'Z', 135.475),
            ('plunger', 0),
        ])
        move_to_sample.assert_not_called()
        sample.setVolume.assert_called_once_with(10.0)


    def test_uptakeLiquidSinglePosition_rejects_more_than_available(self):
        sample = MagicMock()
        sample.getVolume.return_value = 10

        with patch.object(self.ber, 'movePipetteToVolume') as move_plunger:
            with self.assertRaises(ValueError):
                self.ber.uptakeLiquidSinglePosition(sample, 20)

        move_plunger.assert_not_called()


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

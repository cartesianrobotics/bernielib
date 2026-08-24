import importlib.util
import os
import unittest

from unittest.mock import ANY, MagicMock, call, patch


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(
    REPO_ROOT,
    'experiments',
    '20260823_coordinated_wall_wash',
    'scripts',
    'physical_experiment_coordinated_wall_wash.py',
)

SPEC = importlib.util.spec_from_file_location('coordinated_wall_wash_experiment',
                                              SCRIPT_PATH)
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)


class coordinated_wall_wash_experiment_test_case(unittest.TestCase):

    def test_sample_setup_maps_tube_yellow_source_and_liquid_waste(self):
        ber = MagicMock()
        tube = MagicMock()
        yellow = MagicMock()
        liquid_waste = MagicMock()

        with patch.object(experiment.bl, 'createSample',
                          side_effect=[tube, yellow, liquid_waste]) as create:
            result = experiment.makeSamples('run_id', ber)

        self.assertEqual(result, (tube, yellow, liquid_waste))
        self.assertEqual(create.call_args_list, [
            call('eppendorf', ANY, ber.samples_rack, pos_col=1, pos_row=0,
                 volume=0, purge=True),
            call('25mL', ANY, ber.reagents_rack, pos_col=0, pos_row=2,
                 volume=25000.0, purge=True),
            call('25mL', ANY, ber.reagents_rack, pos_col=0, pos_row=1,
                 volume=0, purge=True),
        ])

    def test_wall_wash_approaches_high_then_queues_three_descending_segments(self):
        events = []
        ber = MagicMock()
        sample = MagicMock()
        sample.getCenterXY.return_value = (157.87, 20.1)
        sample.getSampleTopAbsZ.return_value = 99.0
        sample.getVolume.return_value = 10
        ber._calcExtraLength.return_value = 41.6
        ber.calcPipettePositionFromVolume.side_effect = [1.0, 2.0, 3.0]
        ber.moveAxis.side_effect = lambda axis, z: events.append(('vertical', axis, z))
        ber.moveXY.side_effect = lambda x, y: events.append(('horizontal', x, y))
        ber.moveCoordinated.side_effect = lambda **move: events.append(
            ('coordinated', move['z'], move['a']))
        ber.powerStepperOff.side_effect = lambda axis: events.append(('poweroff', axis))

        with patch('builtins.print'):
            completed_at = experiment.coordinatedWallWash(
                ber, sample, volume=20, feed_rate=600)

        self.assertEqual(ber.moveAxis.call_args_list, [
            call('Z', 123.0),
            call('Z', 123.0),
        ])
        self.assertEqual(ber.moveCoordinated.call_args_list, [
            call(x=160.87, y=20.1, z=127.0, a=1.0, speed=600,
                 wait=False, poweroff_a=False),
            call(x=160.241, y=20.1, z=131.0, a=2.0, speed=600,
                 wait=False, poweroff_a=False),
            call(x=159.612, y=20.1, z=135.0, a=3.0, speed=600,
                 wait=True, poweroff_a=False),
        ])
        self.assertEqual(ber.moveXY.call_args_list, [
            call(160.87, 20.1),
            call(157.87, 20.1),
        ])
        self.assertEqual(events, [
            ('vertical', 'Z', 123.0),
            ('horizontal', 160.87, 20.1),
            ('coordinated', 127.0, 1.0),
            ('coordinated', 131.0, 2.0),
            ('coordinated', 135.0, 3.0),
            ('poweroff', 'A'),
            ('horizontal', 157.87, 20.1),
            ('vertical', 'Z', 123.0),
        ])
        sample.setVolume.assert_called_once_with(30)
        self.assertIsInstance(completed_at, float)

    def test_timing_measures_each_aspiration_through_its_final_dispense(self):
        ber = MagicMock()
        sample = MagicMock()

        with patch.object(experiment.time, 'perf_counter', side_effect=[10.0, 20.0, 30.0]), \
                patch.object(experiment, 'coordinatedWallWash',
                             side_effect=[15.0, 28.0, 40.0]) as wash, \
                patch('builtins.print'):
            timings = experiment.performTimedWallWashes(ber, sample, feed_rate=600)

        self.assertEqual(ber.uptakeLiquidSinglePosition.call_args_list, [
            call(sample, 20.0),
            call(sample, 20.0),
            call(sample, 20.0),
        ])
        self.assertEqual(wash.call_args_list, [
            call(ber, sample, 20.0, 600),
            call(ber, sample, 20.0, 600),
            call(ber, sample, 20.0, 600),
        ])
        self.assertEqual(timings['wash_durations_seconds'], [5.0, 8.0, 10.0])
        self.assertAlmostEqual(timings['mean_wash_duration_seconds'], 23.0 / 3.0)
        self.assertEqual(timings['first_aspiration_to_last_dispense_seconds'], 30.0)

    def test_experiment_performs_requested_robot_actions_in_order(self):
        events = []
        ber = MagicMock()
        sample = MagicMock()
        yellow = MagicMock()
        liquid_waste = MagicMock()
        liquid_waste.getVolume.return_value = 0
        state = {'tip_may_be_attached': False}
        ber.home.side_effect = lambda: events.append('home')
        ber.pickUpNextTip.side_effect = lambda: (events.append('pick tip') or (0, 0))
        ber.moveAxisDelta.side_effect = lambda *args, **kwargs: events.append('raise 30')
        ber.uptakeLiquid.side_effect = lambda *args, **kwargs: events.append('uptake')
        ber.transferLiquid.side_effect = lambda source, *args, **kwargs: events.append(
            'seed tube' if source is yellow else 'empty to liquid waste')
        ber.move.side_effect = lambda *args, **kwargs: events.append('safe retreat')
        ber.dumpTipToWaste.side_effect = lambda: events.append('tip waste')
        timing_result = {'wash_durations_seconds': [1.0, 1.0, 1.0]}

        with patch.object(experiment, 'performTimedWallWashes',
                          side_effect=lambda *args, **kwargs:
                          (events.append('three timed washes') or timing_result)), \
                patch('builtins.print'):
            result = experiment.executeExperiment(
                ber, sample, yellow, liquid_waste, feed_rate=600, state=state)

        self.assertEqual(events, [
            'home',
            'pick tip',
            'raise 30',
            'seed tube',
            'three timed washes',
            'empty to liquid waste',
            'safe retreat',
            'tip waste',
            'home',
        ])
        self.assertIs(result, timing_result)
        self.assertFalse(state['tip_may_be_attached'])
        ber.moveAxisDelta.assert_called_once_with('Z', -30.0)
        self.assertEqual(ber.transferLiquid.call_args_list, [
            call(yellow, sample, 30.0, touch_wall=False, safe_z=50.0),
            call(sample, liquid_waste, 30.0, dry_tube=True,
                 touch_wall=False, safe_z=50.0),
        ])
        liquid_waste.setVolume.assert_called_once_with(30.0)
        ber.move.assert_called_once_with(z=50.0)

    def test_default_script_mode_never_constructs_a_robot(self):
        with patch.object(experiment, 'requireRepoRootCwd'), \
                patch.object(experiment.bl, 'robot') as robot_constructor, \
                patch('builtins.print'):
            result = experiment.main([])

        self.assertEqual(result, 0)
        robot_constructor.assert_not_called()

    def test_invalid_real_feed_rate_is_rejected_before_robot_construction(self):
        with patch.object(experiment, 'requireRepoRootCwd'), \
                patch.object(experiment.bl, 'robot') as robot_constructor:
            with self.assertRaises(SystemExit):
                experiment.main(['--move-the-robot', '--feed-rate', 'nan'])

        robot_constructor.assert_not_called()


if __name__ == '__main__':
    unittest.main()

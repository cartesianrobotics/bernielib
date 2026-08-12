"""
Tests for the per-tube-type dispense height.

Roche reported in January 2022 that "the height of dispense is still too high".
The insert depth was a constant: maximum tube volume less extra_vol_insert, with
a `# TODO: create sample type setting for that` on the line. dispenseLiquid() now
takes calc_insert_vol_as, and the level can be recorded per tube type.

The point of most of these tests is the fallback. No tube type shipped today
carries liquid_dispense_vol_level, and getLiquidDispenseVolLevel() returns None
for all of them, so the new default path has to reproduce the old arithmetic
exactly. A working copy of this change from 2022 defaulted to the setting with no
fallback, which would have driven every dispense through
calcAbsLiquidLevelFromVol(None).

No hardware: the serial port is mocked, and the Z the robot would move to is read
off a mocked moveToSample().
"""

import logging
import unittest
from unittest.mock import patch

import bernielib as bl


TUBE_TYPE = 'eppendorf'
EXTRA_VOL_INSERT = 100


class dispense_height_test_case(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        serial_patcher = patch('serial.Serial')
        serial_patcher.start()
        self.addCleanup(serial_patcher.stop)
        # Nothing here may reach the real settings files. _setSetting writes to the
        # in-memory dict and then saves, so blocking save() exercises the real logic
        # while leaving eppendorf.json and the rest untouched.
        save_patcher = patch('bernielib.data.save')
        save_patcher.start()
        self.addCleanup(save_patcher.stop)
        with patch('time.sleep'):
            self.ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')
        self.sample = bl.createSample(TUBE_TYPE, 'test_sample',
                                      self.ber.samples_rack, 1, 0, volume=100)
        # A tube type is shared state loaded from disk; make sure this test starts
        # from "no level recorded" whatever ran before it.
        self.sample.stype.data.pop('liquid_dispense_vol_level', None)

    def tearDown(self):
        self.ber.close()
        del self.ber
        logging.disable(logging.NOTSET)

    def dispenseAndReturnInsertZ(self, **kwargs):
        """Runs a dispense with everything that moves stubbed, and reports the insert Z."""
        with patch.object(bl.robot, 'moveToSample') as move_to_sample, \
             patch.object(bl.robot, 'movePipetteToVolume'), \
             patch.object(bl.robot, 'move'), \
             patch.object(bl.robot, 'pipetteMove'), \
             patch.object(bl.robot, 'getPipetteDelay', return_value=0):
            self.ber.dispenseLiquid(self.sample, volume=50,
                                    extra_vol_insert=EXTRA_VOL_INSERT, **kwargs)
            self.assertTrue(move_to_sample.called, "dispenseLiquid did not move to the sample")
            return move_to_sample.call_args[1]['z']

    def expectedZForVolumeLevel(self, volume_level):
        return self.sample.calcAbsLiquidLevelFromVol(
            volume_level, added_length=self.ber._calcExtraLength())


    # ------------------------------------------------------------------
    # The tube type setting
    # ------------------------------------------------------------------

    def test_levelIsAbsentUntilItIsSet(self):
        self.assertIsNone(self.sample.stype.getLiquidDispenseVolLevel())

    def test_levelRoundTrips(self):
        self.sample.stype.setLiquidDispenseVolLevel(500)

        self.assertEqual(self.sample.stype.getLiquidDispenseVolLevel(), 500)

    def test_readingAnAbsentLevelDoesNotLogErrors(self):
        """
        _getSetting() logs three error lines for a missing key, and this is read on
        every dispense. getLiquidDispenseVolLevel() checks presence first to avoid
        filling the protocol log with errors about a normal condition.
        """
        logging.disable(logging.NOTSET)
        with self.assertLogs(level='ERROR') as captured:
            logging.error("placeholder so assertLogs always has a record")
            self.sample.stype.getLiquidDispenseVolLevel()

        self.assertEqual(len(captured.records), 1,
                         "reading an absent level logged: %s"
                         % [r.getMessage() for r in captured.records[1:]])


    # ------------------------------------------------------------------
    # Nothing changes until a level is set - the important part
    # ------------------------------------------------------------------

    def test_defaultMatchesTheOldBehaviourWhenNoLevelIsSet(self):
        """The pre-change arithmetic, reproduced exactly."""
        expected = self.expectedZForVolumeLevel(
            self.sample.stype.getMaxVolume() - EXTRA_VOL_INSERT)

        z = self.dispenseAndReturnInsertZ()

        self.assertAlmostEqual(z, expected, places=6)

    def test_defaultAndMaxvolAgreeWhenNoLevelIsSet(self):
        z_default = self.dispenseAndReturnInsertZ()
        z_maxvol = self.dispenseAndReturnInsertZ(calc_insert_vol_as='maxvol')

        self.assertAlmostEqual(z_default, z_maxvol, places=6)

    def test_extraVolInsertStillMovesTheHeightWhenNoLevelIsSet(self):
        """The old parameter has to keep working on the fallback path."""
        shallow = self.dispenseAndReturnInsertZ(calc_insert_vol_as='maxvol')
        with patch.object(bl.robot, 'moveToSample') as move_to_sample, \
             patch.object(bl.robot, 'movePipetteToVolume'), \
             patch.object(bl.robot, 'move'), \
             patch.object(bl.robot, 'pipetteMove'), \
             patch.object(bl.robot, 'getPipetteDelay', return_value=0):
            self.ber.dispenseLiquid(self.sample, volume=50, extra_vol_insert=500,
                                    calc_insert_vol_as='maxvol')
            deeper = move_to_sample.call_args[1]['z']

        self.assertGreater(deeper, shallow,
                           "a larger extra_vol_insert should insert deeper (larger Z)")


    # ------------------------------------------------------------------
    # The setting takes effect once set
    # ------------------------------------------------------------------

    def test_settingTheLevelChangesTheInsertHeight(self):
        self.sample.stype.setLiquidDispenseVolLevel(400)
        expected = self.expectedZForVolumeLevel(400)

        z = self.dispenseAndReturnInsertZ()

        self.assertAlmostEqual(z, expected, places=6)

    def test_aLowerLevelDispensesDeeper(self):
        """
        The whole point of the change: Roche wanted to dispense lower down. Z counts
        downward, so deeper is a larger Z.
        """
        self.sample.stype.setLiquidDispenseVolLevel(1000)
        higher = self.dispenseAndReturnInsertZ()
        self.sample.stype.setLiquidDispenseVolLevel(200)
        lower = self.dispenseAndReturnInsertZ()

        self.assertGreater(lower, higher,
                           "a lower volume level should put the tip deeper into the tube")

    def test_maxvolIgnoresTheSettingEvenWhenPresent(self):
        self.sample.stype.setLiquidDispenseVolLevel(400)
        expected = self.expectedZForVolumeLevel(
            self.sample.stype.getMaxVolume() - EXTRA_VOL_INSERT)

        z = self.dispenseAndReturnInsertZ(calc_insert_vol_as='maxvol')

        self.assertAlmostEqual(z, expected, places=6)

    def test_settingTheLevelDoesNotDisturbOtherTubeTypes(self):
        other = bl.createSample('5mL', 'other_sample', self.ber.samples_rack, 1, 1, volume=100)
        other.stype.data.pop('liquid_dispense_vol_level', None)
        self.sample.stype.setLiquidDispenseVolLevel(400)

        self.assertIsNone(other.stype.getLiquidDispenseVolLevel())


    # ------------------------------------------------------------------
    # A mistyped mode must not silently dispense from the top
    # ------------------------------------------------------------------

    def test_unknownModeRaises(self):
        """
        The 2022 working copy assigned the full tube volume before its if/elif, so an
        unrecognised value fell through to the shallowest possible insertion - silently
        producing the exact fault this change exists to fix.
        """
        with self.assertRaises(ValueError):
            self.dispenseAndReturnInsertZ(calc_insert_vol_as='setttings')

    def test_unknownModeNamesTheOffendingValue(self):
        try:
            self.dispenseAndReturnInsertZ(calc_insert_vol_as='maxvolume')
        except ValueError as e:
            self.assertIn('maxvolume', str(e))
        else:
            self.fail("expected a ValueError")


if __name__ == '__main__':
    unittest.main()

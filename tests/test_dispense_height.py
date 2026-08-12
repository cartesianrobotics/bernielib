"""
Tests for how deep the tip goes when dispensing.

Roche reported in January 2022 that "the height of dispense is still too high".
The insert depth was a constant - maximum tube volume less extra_vol_insert -
with a "TODO: create sample type setting for that" on the line. It is now a
(mode, value) pair, either passed to dispenseLiquid() or recorded per tube type.

Two things these tests are really guarding.

The fallback. No tube type carries a level today, so the default path has to
reproduce the old arithmetic exactly, or adopting this changes how every existing
protocol dispenses. A 2022 working copy of this change read the setting with no
fallback, which would have sent every dispense through
calcAbsLiquidLevelFromVol(None).

The pair staying whole. The value is microlitres under 'vol_headroom' and
millimetres under the others, so a mode and value that get separated are silently
wrong rather than noisily broken.

No hardware: the serial port is mocked, and heights are read from
calcDispenseInsertZ() or off a mocked moveToSample().
"""

import logging
import unittest
from unittest.mock import patch

import bernielib as bl
import samples


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
        # Tube types and samples are loaded from disk and shared; start from a known
        # state whatever ran before.
        self.sample.stype.data.pop('dispense_insert_level', None)
        self.sample.data.pop('tube_bottom_z', None)

    def tearDown(self):
        self.ber.close()
        del self.ber
        logging.disable(logging.NOTSET)

    def insertZ(self, volume=50, **kwargs):
        return self.ber.calcDispenseInsertZ(self.sample, volume,
                                            extra_vol_insert=EXTRA_VOL_INSERT, **kwargs)

    def zForVolume(self, volume_level):
        return self.sample.calcAbsLiquidLevelFromVol(
            volume_level, added_length=self.ber._calcExtraLength())


    # ------------------------------------------------------------------
    # Nothing changes until a level is set
    # ------------------------------------------------------------------

    def test_defaultReproducesTheOldArithmetic(self):
        expected = self.zForVolume(self.sample.stype.getMaxVolume() - EXTRA_VOL_INSERT)

        self.assertAlmostEqual(self.insertZ(), expected, places=6)

    def test_extraVolInsertStillWorksOnTheFallbackPath(self):
        shallow = self.insertZ()
        deeper = self.ber.calcDispenseInsertZ(self.sample, 50, extra_vol_insert=500)

        self.assertGreater(deeper, shallow,
                           "a larger extra_vol_insert should insert deeper (larger Z)")

    def test_dispenseLiquidUsesTheCalculatedHeight(self):
        """The height reaches the machine, not just the helper."""
        expected = self.insertZ(volume=50)
        with patch.object(bl.robot, 'moveToSample') as move_to_sample, \
             patch.object(bl.robot, 'movePipetteToVolume'), \
             patch.object(bl.robot, 'move'), \
             patch.object(bl.robot, 'getPipetteDelay', return_value=0):
            self.ber.dispenseLiquid(self.sample, volume=50,
                                    extra_vol_insert=EXTRA_VOL_INSERT)

        self.assertAlmostEqual(move_to_sample.call_args[1]['z'], expected, places=6)

    def test_readingAnAbsentLevelDoesNotLogErrors(self):
        """
        _getSetting() logs three error lines for a missing key, and this is read on
        every dispense; a normal condition must not fill the protocol log.
        """
        logging.disable(logging.NOTSET)
        with self.assertLogs(level='ERROR') as captured:
            logging.error("placeholder so assertLogs always has a record")
            self.sample.stype.getDispenseInsertLevel()

        self.assertEqual(len(captured.records), 1,
                         "reading an absent level logged: %s"
                         % [r.getMessage() for r in captured.records[1:]])


    # ------------------------------------------------------------------
    # vol_headroom - the default mode, and the only self-adjusting one
    # ------------------------------------------------------------------

    def test_volHeadroomSitsAboveTheFinalSurface(self):
        self.sample.setVolume(100)
        expected = self.zForVolume(100 + 50 + 30)   # in tube + dispensed + headroom

        self.assertAlmostEqual(self.insertZ(volume=50, insert_level=('vol_headroom', 30)),
                               expected, places=6)

    def test_volHeadroomRisesAsTheTubeFills(self):
        """
        The property that makes one number work for a tube at any fill level: a fuller
        tube must dispense higher up. Z counts downward, so higher is a smaller Z.
        """
        self.sample.setVolume(100)
        nearly_empty = self.insertZ(volume=50, insert_level=('vol_headroom', 30))
        self.sample.setVolume(900)
        nearly_full = self.insertZ(volume=50, insert_level=('vol_headroom', 30))

        self.assertLess(nearly_full, nearly_empty,
                        "a fuller tube should be dispensed into higher up")

    def test_volHeadroomAccountsForTheVolumeBeingDispensed(self):
        """Not just what is in the tube now - what will be in it afterwards."""
        self.sample.setVolume(100)
        small = self.insertZ(volume=10, insert_level=('vol_headroom', 30))
        large = self.insertZ(volume=500, insert_level=('vol_headroom', 30))

        self.assertLess(large, small,
                        "dispensing more should place the tip higher, above the final level")

    def test_moreHeadroomIsShallower(self):
        self.sample.setVolume(100)
        tight = self.insertZ(volume=50, insert_level=('vol_headroom', 10))
        generous = self.insertZ(volume=50, insert_level=('vol_headroom', 400))

        self.assertLess(generous, tight)

    def test_volHeadroomClampsAtTheRim(self):
        """
        Without a clamp, getDepthFromVolume() extrapolates past the top of its table and
        returns a Z above the tube - and above the rack.
        """
        self.sample.setVolume(1600)
        z = self.insertZ(volume=500, insert_level=('vol_headroom', 500))

        self.assertAlmostEqual(z, self.zForVolume(self.sample.stype.getMaxVolume()),
                               places=6)


    # ------------------------------------------------------------------
    # The other two modes
    # ------------------------------------------------------------------

    def test_zFromTopIsMeasuredDownFromTheRim(self):
        expected = self.sample.calcSampleAbsZFromZRelativeToTop(
            5, added_length=self.ber._calcExtraLength())

        self.assertAlmostEqual(self.insertZ(insert_level=('z_from_top', 5)),
                               expected, places=6)

    def test_zFromTopIgnoresHowFullTheTubeIs(self):
        self.sample.setVolume(100)
        empty = self.insertZ(insert_level=('z_from_top', 5))
        self.sample.setVolume(1500)
        full = self.insertZ(insert_level=('z_from_top', 5))

        self.assertAlmostEqual(empty, full, places=6)

    def test_zFromBottomIsMeasuredUpFromTheCalibratedBottom(self):
        self.sample.setZBottom(170.0)

        self.assertAlmostEqual(self.insertZ(insert_level=('z_from_bottom', 10)),
                               160.0, places=6)

    def test_zFromBottomNeedsACalibratedBottom(self):
        """Silently guessing a bottom would drive the tip into the tube."""
        with self.assertRaises(ValueError) as caught:
            self.insertZ(insert_level=('z_from_bottom', 10))

        self.assertIn('calibrated', str(caught.exception))


    # ------------------------------------------------------------------
    # The pair, and the tube type setting
    # ------------------------------------------------------------------

    def test_levelIsAbsentUntilItIsSet(self):
        self.assertIsNone(self.sample.stype.getDispenseInsertLevel())

    def test_levelRoundTripsAsAPair(self):
        self.sample.stype.setDispenseInsertLevel('vol_headroom', 30)

        self.assertEqual(self.sample.stype.getDispenseInsertLevel(), ('vol_headroom', 30))

    def test_theTubeTypeLevelIsUsedWhenNoneIsPassed(self):
        self.sample.setVolume(100)
        self.sample.stype.setDispenseInsertLevel('vol_headroom', 30)

        self.assertAlmostEqual(self.insertZ(volume=50), self.zForVolume(180), places=6)

    def test_anExplicitLevelOverridesTheTubeType(self):
        self.sample.stype.setDispenseInsertLevel('vol_headroom', 30)
        expected = self.sample.calcSampleAbsZFromZRelativeToTop(
            5, added_length=self.ber._calcExtraLength())

        self.assertAlmostEqual(self.insertZ(insert_level=('z_from_top', 5)),
                               expected, places=6)

    def test_settingALevelDoesNotDisturbOtherTubeTypes(self):
        other = bl.createSample('5mL', 'other_sample', self.ber.samples_rack, 1, 1, volume=100)
        other.stype.data.pop('dispense_insert_level', None)
        self.sample.stype.setDispenseInsertLevel('vol_headroom', 30)

        self.assertIsNone(other.stype.getDispenseInsertLevel())

    def test_unknownModeRaisesWhenPassed(self):
        with self.assertRaises(ValueError) as caught:
            self.insertZ(insert_level=('vol_headrooom', 30))

        self.assertIn('vol_headrooom', str(caught.exception))

    def test_unknownModeRaisesWhenStored(self):
        """Caught on the way in, so a bad value cannot sit in a JSON file waiting."""
        with self.assertRaises(ValueError):
            self.sample.stype.setDispenseInsertLevel('headroom', 30)

    def test_aBareValueIsRejected(self):
        """
        The whole reason mode and value travel together: 30 alone could be microlitres
        or millimetres.
        """
        with self.assertRaises(ValueError):
            self.insertZ(insert_level=30)

    def test_everyDocumentedModeIsAccepted(self):
        """The mode table and the dispatch must not drift apart."""
        self.sample.setZBottom(170.0)
        for mode in samples.DISPENSE_INSERT_MODES:
            with self.subTest(mode=mode):
                self.assertIsInstance(self.insertZ(insert_level=(mode, 5)), float)


if __name__ == '__main__':
    unittest.main()

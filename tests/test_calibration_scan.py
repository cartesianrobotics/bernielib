"""
Tests for the bounded edge search and the rack-centre re-seeding.

Both exist because of a real failure on 2026-08-07: the deck had shifted 2 mm in
X since the tips rack was last calibrated, so the tips edge scan started just
past the rack edge, found no edge, and - having no limit on how far it could
travel - tapped its way 16 mm across onto the neighbouring rack. The centre came
out 7.1 mm wrong, which then put the Z-calibration probe on top of a tip instead
of the rack frame, and the robot picked the tip up.

No hardware: a FakeDeck answers the probing, and nothing is written to disk.
"""

import logging
import unittest
from unittest.mock import patch

import bernielib as bl


SURFACE_Z = 147.0   # top of a rack
DECK_Z = 167.0      # bare deck, 20 mm lower - far past any edge threshold

# Geometry of the failure, in machine coordinates.
TRUE_RACK_MIN = 26.495      # where the tips rack edge actually was
TRUE_RACK_MAX = 113.745
STALE_SCAN_START = 24.495   # where the stale centre said to start: 2 mm off the rack


class FakeDeck:
    """
    A one-axis deck for the scans to feel their way along.

    The rack occupies [rack_min, rack_max] in X and stands SURFACE_Z high;
    everywhere else reads DECK_Z. Records every X the pipette is sent to, so a
    test can assert where it did and did not go.
    """

    def __init__(self, rack_min, rack_max):
        self.rack_min = rack_min
        self.rack_max = rack_max
        self.x = 0.0
        self.z = 145.0
        self.visited_x = []

    def heightAt(self, x):
        if self.rack_min <= x <= self.rack_max:
            return SURFACE_Z
        return DECK_Z


def attachFakeDeck(ber, deck, max_travel=8, backtrack=4, max_retries=5):
    """
    Replaces the robot's motion and probing with the fake deck, and pins the
    search parameters so the tests do not depend on the machine's settings file.
    """

    def getPosition(axis=None):
        if axis == 'X':
            return deck.x
        if axis == 'Z':
            return deck.z
        return deck.x, 0.0, deck.z, 0.0

    def moveAxis(axis, dist, speed=None):
        if axis.upper() == 'X':
            deck.x = dist
            deck.visited_x.append(dist)
        elif axis.upper() == 'Z':
            deck.z = dist

    def moveAxisDelta(axis, dist, speed=None):
        if axis.upper() == 'X':
            moveAxis('X', deck.x + dist)
        elif axis.upper() == 'Z':
            moveAxis('Z', deck.z + dist)

    def moveDownUntilPress(step, threshold, z_max=180, tare=True):
        # Descends until it meets whatever is under the pipette, or z_max.
        deck.z = min(deck.heightAt(deck.x), z_max)
        return deck.z

    ber.getPosition = getPosition
    ber.moveAxis = moveAxis
    ber.moveAxisDelta = moveAxisDelta
    ber.moveDownUntilPress = moveDownUntilPress
    # step_list, z_increment, z_retract, z_max_travel, z_threshold
    ber.getPositioningParameters = lambda: ([1, 0.2], 0.1, -1, 3, 500)
    ber.getStairSearchMaxTravel = lambda: max_travel
    ber.getStairSearchBacktrack = lambda: backtrack
    ber.getStairSearchMaxRetries = lambda: max_retries
    return ber


class calibration_scan_test_case(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        serial_patcher = patch('serial.Serial')
        serial_patcher.start()
        self.addCleanup(serial_patcher.stop)
        # Nothing in these tests may reach the real settings files: _setSetting
        # updates the in-memory dict and then saves, so blocking save() keeps the
        # real logic intact while leaving the machine's calibration untouched.
        save_patcher = patch('bernielib.data.save')
        save_patcher.start()
        self.addCleanup(save_patcher.stop)
        with patch('time.sleep'):
            self.ber = bl.robot(cartesian_port_name='COM18', loadcell_port_name='COM7')

    def tearDown(self):
        self.ber.close()
        del self.ber
        logging.disable(logging.NOTSET)


    # ------------------------------------------------------------------
    # 1. Scans that find the edge
    # ------------------------------------------------------------------

    def test_findsEdgeScanningTowardsSmallerCoordinate(self):
        """Start 2 mm inside the rack, scan outward, land on the edge."""
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck)
        deck.x = TRUE_RACK_MIN + 2.0

        edge = self.ber.scanForStairFine('X', direction=-1)

        self.assertAlmostEqual(edge, TRUE_RACK_MIN, delta=1.0)

    def test_findsEdgeScanningTowardsLargerCoordinate(self):
        """The opposite edge, scanned the other way: the sign handling holds."""
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck)
        deck.x = TRUE_RACK_MAX - 2.0

        edge = self.ber.scanForStairFine('X', direction=1)

        self.assertAlmostEqual(edge, TRUE_RACK_MAX, delta=1.0)

    def test_scanForStairReturnsCoordinateNotNoneOnSuccess(self):
        """The coarse scan alone reports the edge rather than the None sentinel."""
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck)
        deck.x = TRUE_RACK_MIN + 3.0
        deck.z = SURFACE_Z

        found = self.ber.scanForStair('X', step=1, direction=-1)

        self.assertIsNotNone(found)
        self.assertAlmostEqual(found, TRUE_RACK_MIN, delta=1.5)


    # ------------------------------------------------------------------
    # 2. Scans that fail to find the edge - the runaway protection
    # ------------------------------------------------------------------

    def test_scanForStairGivesUpInsteadOfWalkingAway(self):
        """
        Starting off the rack, on flat deck, there is no edge to find. Before the
        fix this loop had no lateral bound at all.
        """
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck)
        deck.x = STALE_SCAN_START
        deck.z = DECK_Z          # already probed down onto the deck

        found = self.ber.scanForStair('X', step=1, direction=-1)

        self.assertIsNone(found)

    def test_scanForStairStopsWithinMaxTravel(self):
        """The give-up happens after max_travel, not somewhere across the deck."""
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck, max_travel=8)
        deck.x = STALE_SCAN_START
        deck.z = DECK_Z

        self.ber.scanForStair('X', step=1, direction=-1)

        travelled = STALE_SCAN_START - min(deck.visited_x)
        self.assertLessEqual(travelled, 8 + 1,
                             "scan travelled %.1f mm, past the 8 mm bound" % travelled)

    def test_backtracksTheOtherWayAndRecoversTheEdge(self):
        """
        Replay of the 2026-08-07 failure: the scan is seeded 2 mm past the true
        edge. It must step back the other way - onto the rack - and find it.
        """
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck, max_travel=8, backtrack=4)
        deck.x = STALE_SCAN_START

        edge = self.ber.scanForStairFine('X', direction=-1)

        self.assertAlmostEqual(edge, TRUE_RACK_MIN, delta=1.0)

    def test_backtrackMovesAgainstTheScanDirection(self):
        """
        The retry must move opposite to the scan, i.e. back onto the object.
        Moving further along would only take it further away.
        """
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck, max_travel=8, backtrack=4)
        deck.x = STALE_SCAN_START

        self.ber.scanForStairFine('X', direction=-1)

        self.assertIn(STALE_SCAN_START + 4, deck.visited_x,
                      "expected a retry to restart 4 mm in the +X direction")

    def test_neverReachesTheNeighbouringRack(self):
        """
        The live failure ran 16 mm out, onto the samples rack at about x=8.
        Nothing may travel that far now.
        """
        deck = FakeDeck(TRUE_RACK_MIN, TRUE_RACK_MAX)
        attachFakeDeck(self.ber, deck, max_travel=8, backtrack=4)
        deck.x = STALE_SCAN_START

        self.ber.scanForStairFine('X', direction=-1)

        self.assertGreater(min(deck.visited_x), 15.0,
                           "pipette wandered to x=%.1f, towards the neighbouring rack"
                           % min(deck.visited_x))

    def test_raisesAfterMaxRetriesWhenThereIsNoRackAtAll(self):
        """With nothing under the pipette, the search must abort, not persist."""
        deck = FakeDeck(rack_min=1000, rack_max=2000)   # nowhere near the pipette
        attachFakeDeck(self.ber, deck, max_retries=5)
        deck.x = 50.0

        with self.assertRaises(bl.CalibrationScanError):
            self.ber.scanForStairFine('X', direction=-1)

    def test_retriesExactlyMaxRetriesTimesBeforeAborting(self):
        """One initial attempt plus max_retries retries, then it stops trying."""
        deck = FakeDeck(rack_min=1000, rack_max=2000)
        attachFakeDeck(self.ber, deck, max_retries=5)
        deck.x = 50.0
        attempts = []
        real_scanForStair = self.ber.scanForStair

        def countingScanForStair(*args, **kwargs):
            attempts.append(1)
            return real_scanForStair(*args, **kwargs)

        self.ber.scanForStair = countingScanForStair

        with self.assertRaises(bl.CalibrationScanError):
            self.ber.scanForStairFine('X', direction=-1)

        # Each failing attempt breaks out of the step list after the first step,
        # so attempts map one-to-one onto scanForStair calls.
        self.assertEqual(len(attempts), 6)

    def test_totalSearchIsBounded(self):
        """5 retries x 4 mm, plus 8 mm of scanning each: it cannot creep away."""
        deck = FakeDeck(rack_min=1000, rack_max=2000)
        attachFakeDeck(self.ber, deck, max_travel=8, backtrack=4, max_retries=5)
        deck.x = 50.0

        with self.assertRaises(bl.CalibrationScanError):
            self.ber.scanForStairFine('X', direction=-1)

        span = max(deck.visited_x) - min(deck.visited_x)
        self.assertLess(span, 60.0, "search covered %.1f mm" % span)


    # ------------------------------------------------------------------
    # 3. Re-seeding the tips centre from the calibrated samples rack
    # ------------------------------------------------------------------

    def calibrateSamplesRackTo(self, x, y):
        """Stands in for calibrateRack('samples') having just measured a centre."""
        self.ber.samples_rack.setCenterXY(x=x, y=y)

    def test_offsetRoundTrips(self):
        self.ber.tips_rack.setCenterOffsetFromReference(-17.88, -27.0,
                                                        reference_rack='samples')

        dx, dy, reference = self.ber.tips_rack.getCenterOffsetFromReference()

        self.assertAlmostEqual(dx, -17.88)
        self.assertAlmostEqual(dy, -27.0)
        self.assertEqual(reference, 'samples')

    def test_staleTipsCentreIsReplacedAfterSamplesCalibration(self):
        """
        The exact numbers from 2026-08-07: the deck moved 2 mm, samples measured
        88.0, and the stale tips centre of 68.12 must become 70.12.
        """
        self.ber.tips_rack.setCenterOffsetFromReference(-17.88, -27.0,
                                                        reference_rack='samples')
        self.ber.tips_rack.setCenterXY(x=68.12, y=75.0)     # stale, pre-shift
        self.calibrateSamplesRackTo(88.0, 102.1)            # freshly calibrated

        seeded = self.ber.seedRackCenterFromReference('tips')

        self.assertAlmostEqual(seeded[0], 70.12, places=3)
        self.assertAlmostEqual(seeded[1], 75.1, places=3)
        x, y = self.ber.tips_rack.getCenterXY()
        self.assertAlmostEqual(x, 70.12, places=3)
        self.assertAlmostEqual(y, 75.1, places=3)

    def test_seedingTracksTheReferenceWhereverItMoves(self):
        """A different shift must produce a correspondingly different centre."""
        self.ber.tips_rack.setCenterOffsetFromReference(-17.88, -27.0,
                                                        reference_rack='samples')
        self.ber.tips_rack.setCenterXY(x=68.12, y=75.0)
        self.calibrateSamplesRackTo(80.0, 95.0)             # shifted the other way

        x, y = self.ber.seedRackCenterFromReference('tips')

        self.assertAlmostEqual(x, 80.0 - 17.88, places=3)
        self.assertAlmostEqual(y, 95.0 - 27.0, places=3)

    def test_seedingPutsTheScanStartBackOntoTheRack(self):
        """
        The point of the whole exercise: the calibration start point derived from
        the stale centre sits off the rack, and after seeding it sits on it.
        """
        self.ber.tips_rack.setCenterOffsetFromReference(-17.88, -27.0,
                                                        reference_rack='samples')
        self.ber.tips_rack.setCenterXY(x=68.12, y=75.0)
        self.calibrateSamplesRackTo(88.0, 102.1)

        p1_stale = self.ber.tips_rack.getInitialCalibrationXY()[0]
        self.ber.seedRackCenterFromReference('tips')
        p1_seeded = self.ber.tips_rack.getInitialCalibrationXY()[0]

        self.assertLess(p1_stale[0], TRUE_RACK_MIN,
                        "the stale start point was expected to fall off the rack")
        self.assertGreaterEqual(p1_seeded[0], TRUE_RACK_MIN,
                                "the seeded start point should be on the rack")

    def test_seedingIsSkippedWhenNoOffsetIsRecorded(self):
        """A rack with no recorded offset must be left exactly as it was."""
        self.ber.waste_rack.setCenterXY(x=70.2, y=163.2)
        with patch.object(bl.rack, 'getCenterOffsetFromReference',
                          return_value=(None, None, None)):
            result = self.ber.seedRackCenterFromReference('waste')

        self.assertIsNone(result)
        self.assertEqual(self.ber.waste_rack.getCenterXY(), (70.2, 163.2))


if __name__ == '__main__':
    unittest.main()

"""
Physical test: the edge search stops, backs off, and recovers.

Reproduces the calibration failure of 2026-08-07 on the real machine. The deck
had shifted 2 mm in X since the tips rack was last calibrated, so the edge scan
started just past the rack edge, on flat surface, with no edge ahead of it to
find. Having no limit on travel, it stepped sideways 16 mm onto the neighbouring
rack, recorded a centre 7.1 mm out, and then probed for Z on top of a tip and
picked the tip up.

This test puts the pipette 2 mm outside the true edge on purpose - the same
situation - and checks that it now:

    1. stops after 8 mm rather than walking on,
    2. returns those 8 mm and a further 4 mm past its start, back onto the rack,
    3. finds the real edge on the second attempt.

Step 2 is the point: 4 mm has to be enough to recover from a 2 mm miss. If the
backstep were smaller than the error it would fail again and again until it ran
out of retries, which is a slower way of getting nowhere.

RUN THIS AFTER CALIBRATING THE TIPS RACK. The test derives the true edge from
the stored tips rack centre, and deliberately starts a known 2 mm outside it. If
that centre is stale, "2 mm outside the edge" is not where the pipette actually
goes and the test is measuring nothing. It does not calibrate anything itself:
a full rack calibration is slow and is not what is under test here.

    python physical_tests/physical_test_edge_search.py --move-the-robot

Part of BernieLib.
"""

import sys

from harness import parseArgs, requireRepoRootCwd, physical_test, checklist


# How far outside the nominal edge to start.
#
# This has to exceed the contact bias, or the test cannot do its job. The nozzle
# goes on pressing the rack until its centre has passed the edge by about its own
# radius, so a start only 2 mm out - as this test first had - is still resting on
# the rack, finds the edge at once, and never produces the runaway it is meant to
# reproduce. That is exactly what happened on the first attempt. The bias
# measured 2.2 mm on the tips box, so 5 mm clears it with a couple of millimetres
# to spare, while still leaving the 4 mm backstep landing back on the rack.
START_OUTSIDE_EDGE = 5.0
# The scan reports an edge up to one pipette-end radius inside the nominal one,
# for the same reason. Accept anything within a full diameter inside the nominal
# edge, and no more than a step outside it. A runaway would land far outside this.
EDGE_WINDOW_INSIDE = 5.9    # calibration_common.PIPETTE_END_DIAMETER
EDGE_WINDOW_OUTSIDE = 1.0


def describePlan(ber_settings):
    true_edge, start_x, scan_y, approach_z, max_travel, backtrack = ber_settings
    print("Plan:")
    print("  true tips rack edge (from the stored centre) : %.3f" % true_edge)
    print("  start the scan at                            : %.3f  (%.1f mm outside)"
          % (start_x, START_OUTSIDE_EDGE))
    print("  scan along X towards smaller X, at Y          : %.3f" % scan_y)
    print("  approach height Z                            : %.3f" % approach_z)
    print("  expected: no edge found, stop by             : %.3f  (%.0f mm of travel)"
          % (start_x - max_travel, max_travel))
    print("  expected: retry restarts at                  : %.3f  (%.0f mm past the start)"
          % (start_x + backtrack, backtrack))
    print("  expected: edge then reported between         : %.3f and %.3f"
          % (true_edge - EDGE_WINDOW_INSIDE, true_edge + EDGE_WINDOW_OUTSIDE))
    print("            (the scan reads up to one nozzle radius inside the nominal edge)")


def main():
    args = parseArgs(__doc__)
    requireRepoRootCwd()

    import bernielib as bl

    # Read the geometry before connecting, so --move-the-robot omitted still
    # prints a meaningful plan.
    tips = bl.consumable('tips')
    center_x, center_y = tips.getCenterXY()
    max_x, max_y, max_z = tips.getRackSize()
    y_shift_for_x, x_shift_for_y = tips.getXYCalibrationShift()
    approach_z = tips.getCalibrationZ()

    # 'outer' calibration scans outward from the rack edge towards smaller X.
    true_edge = center_x - max_x / 2.0
    start_x = true_edge - START_OUTSIDE_EDGE
    scan_y = center_y + y_shift_for_x

    # Module defaults for the plan; the robot's own settings are read once it
    # is connected, in case robot.json overrides them.
    max_travel = bl.STAIR_SEARCH_MAX_TRAVEL
    backtrack = bl.STAIR_SEARCH_BACKTRACK

    describePlan((true_edge, start_x, scan_y, approach_z, max_travel, backtrack))

    if not args.confirmed:
        print("\nNothing moved. Re-run with --move-the-robot to perform the test.")
        print("Make sure the tips rack has been calibrated recently, or the starting")
        print("point above is not really %.1f mm outside the edge." % START_OUTSIDE_EDGE)
        return 0

    results = checklist()

    with physical_test('edge search recovery') as ber:
        # Take the search bounds from the robot's own settings now that it exists.
        max_travel = ber.getStairSearchMaxTravel()
        backtrack = ber.getStairSearchBacktrack()

        # Record where the pipette actually goes, as the machine reports it,
        # rather than where we believe we sent it.
        visited_x = []
        real_moveAxis = ber.moveAxis
        real_moveAxisDelta = ber.moveAxisDelta
        real_scanForStair = ber.scanForStair
        attempts = {'total': 0, 'gave_up': 0}

        def recordingMoveAxis(axis, dist, speed=None):
            result = real_moveAxis(axis, dist, speed)
            if axis.upper() == 'X':
                visited_x.append(ber.getPosition(axis='X'))
            return result

        def recordingMoveAxisDelta(axis, dist, speed=None):
            result = real_moveAxisDelta(axis, dist, speed)
            if axis.upper() == 'X':
                visited_x.append(ber.getPosition(axis='X'))
            return result

        def countingScanForStair(*a, **kw):
            attempts['total'] += 1
            found = real_scanForStair(*a, **kw)
            if found is None:
                attempts['gave_up'] += 1
            return found

        print("\n--- Moving to the starting point, %.1f mm outside the edge ---"
              % START_OUTSIDE_EDGE)
        ber.moveAxis('Z', 0)                 # clear of everything before traversing
        ber.move(start_x, scan_y, approach_z, z_first=False)
        print("    at X=%.3f Y=%.3f Z=%.3f"
              % (ber.getPosition('X'), ber.getPosition('Y'), ber.getPosition('Z')))

        ber.moveAxis = recordingMoveAxis
        ber.moveAxisDelta = recordingMoveAxisDelta
        ber.scanForStair = countingScanForStair

        print("\n--- Scanning outward, where there is no edge to find ---")
        edge = None
        error = None
        try:
            edge = ber.scanForStairFine('X', direction=-1)
        except bl.CalibrationScanError as e:
            error = e
        finally:
            ber.moveAxis = real_moveAxis
            ber.moveAxisDelta = real_moveAxisDelta
            ber.scanForStair = real_scanForStair

        print("\n--- Checks ---")
        if not visited_x:
            results.check("the scan moved the X axis", False, "no X movement recorded")
            return results.report()

        furthest_out = min(visited_x)
        travelled = start_x - furthest_out

        results.check(
            "gave up instead of walking on",
            attempts['gave_up'] >= 1,
            "%d of %d scans found no edge" % (attempts['gave_up'], attempts['total']))

        results.check(
            "stopped within %.0f mm of the start" % max_travel,
            travelled <= max_travel + 1.0,
            "travelled %.3f mm, reaching X=%.3f" % (travelled, furthest_out))

        results.check(
            "never reached the neighbouring rack",
            furthest_out > start_x - 12.0,
            "furthest point X=%.3f; the live failure reached about X=8.3" % furthest_out)

        expected_retry_x = start_x + backtrack
        closest = min(visited_x, key=lambda x: abs(x - expected_retry_x))
        results.check(
            "backed off %.0f mm past the start, onto the rack" % backtrack,
            abs(closest - expected_retry_x) < 0.6,
            "expected a restart near X=%.3f, closest visited X=%.3f"
            % (expected_retry_x, closest))

        results.check(
            "recovered and found an edge",
            error is None and edge is not None,
            str(error) if error else "edge at X=%.3f" % edge)

        if edge is not None:
            low = true_edge - EDGE_WINDOW_INSIDE
            high = true_edge + EDGE_WINDOW_OUTSIDE
            results.check(
                "the edge found is the real one",
                low <= edge <= high,
                "found %.3f, nominal edge %.3f, acceptable %.3f..%.3f "
                "(the scan reads up to one nozzle radius inside)"
                % (edge, true_edge, low, high))

        results.check(
            "one backstep was enough for a %.1f mm miss" % START_OUTSIDE_EDGE,
            attempts['gave_up'] == 1,
            "%d attempts gave up; more than one means the backstep is too small"
            % attempts['gave_up'])

    return results.report()


if __name__ == '__main__':
    sys.exit(main())

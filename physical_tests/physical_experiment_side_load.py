"""
Physical experiment: do the load cells see a sideways approach?

Everything the library does with the load cells presses straight down -
moveDownUntilPress(), tube bottom probing, tip pickup. Each of those costs a
descend-and-probe cycle of many small steps. If a sideways touch registers, an
edge could be found with a single approach instead, which is the point of asking.

The nozzle is parked off the right-hand end of the tube rack, below the rack's
top plane, and walked left in small steps, reading both cells at every step.
Orientation: the machine homes to the top right corner, so X=0 is the right and
increasing X moves left, towards the rack.

WHAT THE FIRST RUN FOUND (2026-08-08). Both cells ramp steadily as soon as the
carriage starts moving, long before the nozzle can reach the rack - confirmed
visually, with 2-3 mm still to go. The right cell moves about 2.7 times as far as
the left and in the opposite direction, the ratio holding constant across steps.
So this is the mount reacting to the carriage's own geometry changing as X moves,
not contact. Any rule based on how FAR a reading has moved from its baseline will
fire on that drift every time, which is what happened.

So detection here is not about magnitude but about shape. Free-space drift climbs
by roughly the same amount every step - increment ratios measured 0.73, 0.97 and
0.80 - whereas hitting something makes the increment jump. The trigger is
therefore an increment at least --jump-factor times the previous one,
--jump-consecutive times running. The largest ratio in the recorded drift was
0.97, so a factor of 2 has a wide margin.

Stops at whichever comes first:
  a) the step budget is used up;
  b) the increment jump rule above - an abrupt change, i.e. probably contact;
  c) either cell passes --hard-abort in absolute terms, as a backstop.

Then it retracts to the right, re-reads both cells to see whether the drift was
reversible, lifts, and homes.

    python physical_tests/physical_experiment_side_load.py
    python physical_tests/physical_experiment_side_load.py --move-the-robot
    python physical_tests/physical_experiment_side_load.py --move-the-robot --depth -20

That last one is the control: a negative depth puts the nozzle above the top
plane, where contact is impossible, so whatever it records is drift alone.

ON FORCE. Pressing down is self-limiting - the axis stalls and the cells sit
under the contact. Sideways is not, and the run deliberately carries on past
first contact. Neither stop rule can protect against a force the cells cannot
see. Watch the machine.

Runs with a bare nozzle; the harness ejects any tip first, and the geometry
assumes one. A tip would put the contact 41.6 mm lower.

Part of BernieLib.
"""

import csv
import os
import statistics
import sys

from harness import parseArgs, requireRepoRootCwd, physical_test, checklist
from calibration_common import PIPETTE_END_DIAMETER, timestamp


REPORT_DIR = 'experiment_reports'

# Never start closer than this to the X home limit.
START_MIN_X = 1.0
# An increment has to be at least this large before its ratio to the previous one
# means anything - otherwise two noise-sized increments produce a huge ratio.
# Taken as this many baseline standard deviations, with an absolute floor.
INCREMENT_SIGMA = 3.0
INCREMENT_FLOOR = 0.5


def readBoth(ber, times):
    """Both cells, `times` readings each, returned as two lists."""
    left, right = [], []
    for _ in range(times):
        left.append(ber.readLeftLoad())
        right.append(ber.readRightLoad())
    return left, right


def spread(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def addArgs(parser):
    parser.add_argument('--rack', default='samples',
                        help="Rack whose right-hand side to approach. Default: samples.")
    parser.add_argument('--depth', type=float, default=5.0,
                        help="How far below the rack top plane to approach, mm. Negative "
                             "goes above it, which is the no-contact control. Default: 5.")
    parser.add_argument('--steps', type=int, default=14,
                        help="Maximum number of steps. Default: 14, which carries the "
                             "nozzle about 3 mm past first contact.")
    parser.add_argument('--step-size', type=float, default=0.5,
                        help="Step size in mm. Default: 0.5.")
    parser.add_argument('--start-x', type=float, default=None,
                        help="Override the computed starting X.")
    parser.add_argument('--readings-per-step', type=int, default=3,
                        help="Load cell readings averaged at each step. Default: 3.")
    parser.add_argument('--jump-factor', type=float, default=2.0,
                        help="An increment this many times the previous one counts as a "
                             "jump. Measured drift peaked at 0.97. Default: 2.")
    parser.add_argument('--jump-consecutive', type=int, default=4,
                        help="Consecutive jumps that stop the run. Default: 4.")
    parser.add_argument('--hard-abort', type=float, default=200.0,
                        help="Backstop: stop at once if either cell deviates by more than "
                             "this. 200 is what _probeTubeZBottom() treats as a real "
                             "touch. Cannot protect against a force the cells cannot "
                             "see. Default: 200.")
    parser.add_argument('--gentle-descent', action='store_true',
                        help="Descend to the working height under load supervision, in "
                             "0.5 mm steps. Slow. Off by default: nothing sits above the "
                             "working height at these X coordinates, confirmed visually.")


def main():
    args = parseArgs(__doc__, extra=addArgs)
    requireRepoRootCwd()

    import bernielib as bl

    rack = bl.rack(args.rack)
    center_x, center_y = rack.getCenterXY()
    max_x, max_y, max_z = rack.getRackSize()
    top_plane = rack.getZ()

    edge_x = center_x - max_x / 2.0          # right-hand edge, smallest X
    approach_z = top_plane + args.depth      # Z counts downward
    travel = args.steps * args.step_size

    start_x = args.start_x
    if start_x is None:
        start_x = max(START_MIN_X, edge_x - travel)
    end_x = start_x + travel
    contact_x = edge_x - PIPETTE_END_DIAMETER / 2.0

    control = args.depth < 0
    print("Plan:%s" % ("   [CONTROL - above the rack, contact impossible]" if control else ""))
    print("  rack                            : %s, centre (%.2f, %.2f), body %.1f x %.1f"
          % (args.rack, center_x, center_y, max_x, max_y))
    print("  rack top plane Z                : %.2f" % top_plane)
    print("  approach Z                      : %.2f  (%.1f mm %s the top plane)"
          % (approach_z, abs(args.depth), "below" if args.depth >= 0 else "above"))
    print("  rack right-hand edge at X       : %.2f" % edge_x)
    if not control:
        print("  nozzle first touches it at X    : %.2f" % contact_x)
    print("  start at X                      : %.2f" % start_x)
    print("  walk left to X                  : %.2f  in %d steps of %.2f mm"
          % (end_x, args.steps, args.step_size))
    print("  approach line Y                 : %.2f" % center_y)
    print("  descent                         : %s"
          % ("gentle, load supervised" if args.gentle_descent else "direct"))
    print("  jump rule                       : increment >= %.1fx previous, %d times running"
          % (args.jump_factor, args.jump_consecutive))
    if not control and end_x > contact_x:
        print("  ** the last %.2f mm press INTO the rack. Watch the machine."
              % (end_x - contact_x))

    if not args.confirmed:
        print("\nNothing moved. Re-run with --move-the-robot to perform the experiment.")
        return 0

    os.makedirs(REPORT_DIR, exist_ok=True)
    rows = []
    results = checklist()
    stop_reason = 'step budget exhausted'

    with physical_test('side load sensing') as ber:
        print("\n--- Moving to the start, off the rack to the right ---")
        ber.moveAxis('Z', 0)
        ber.move(start_x, center_y, 0, z_first=False)     # XY at the top, then descend
        if args.gentle_descent:
            reached = ber.moveDownUntilPress(step=0.5, threshold=args.hard_abort,
                                             z_max=approach_z, tare=True)
            if reached < approach_z - 0.6:
                results.check("reached the working height", False,
                              "stopped at Z=%.3f, wanted %.3f - something is in the way"
                              % (reached, approach_z))
                ber.moveAxis('Z', 0)
                return results.report()
        else:
            # Straight down. Nothing sits above the working height at these X
            # coordinates - checked visually on 2026-08-08 - and the stepwise
            # descent cost more time than the walk itself.
            ber.moveAxis('Z', approach_z)
        print("    at X=%.3f Y=%.3f Z=%.3f"
              % (ber.getPosition('X'), ber.getPosition('Y'), ber.getPosition('Z')))
        results.check("reached the working height", True, "Z=%.3f" % ber.getPosition('Z'))

        print("\n--- Baseline, before moving sideways ---")
        ber.tareAll()
        base_left, base_right = readBoth(ber, 10)
        baseline = {
            'left': (statistics.mean(base_left), spread(base_left)),
            'right': (statistics.mean(base_right), spread(base_right)),
        }
        increment_floor = {}
        for side in ('left', 'right'):
            mean, sd = baseline[side]
            increment_floor[side] = max(INCREMENT_SIGMA * sd, INCREMENT_FLOOR)
            print("    %-5s mean %+8.3f, spread %.3f, increments count from %.3f"
                  % (side, mean, sd, increment_floor[side]))

        print("\n--- Walking left in %.2f mm steps ---" % args.step_size)
        print("    %-4s %-8s %-30s %-30s"
              % ("step", "X", "left:  value  dev  inc  ratio", "right: value  dev  inc  ratio"))
        previous_dev = {'left': 0.0, 'right': 0.0}
        previous_inc = {'left': None, 'right': None}
        jump_streak = {'left': 0, 'right': 0}

        for step in range(1, args.steps + 1):
            ber.moveAxisDelta('X', args.step_size)
            x_now = ber.getPosition('X')
            left, right = readBoth(ber, args.readings_per_step)
            reading = {'left': statistics.mean(left), 'right': statistics.mean(right)}
            deviation = {s: reading[s] - baseline[s][0] for s in reading}
            increment = {s: deviation[s] - previous_dev[s] for s in deviation}

            ratio = {}
            for side in ('left', 'right'):
                last = previous_inc[side]
                if last is not None and abs(last) >= increment_floor[side]:
                    ratio[side] = abs(increment[side]) / abs(last)
                else:
                    ratio[side] = None

            def cell(side):
                shown = "  -  " if ratio[side] is None else "%5.2f" % ratio[side]
                return "%8.3f %+7.3f %+7.3f %s" % (reading[side], deviation[side],
                                                   increment[side], shown)
            print("    %-4d %-8.3f %-30s %-30s" % (step, x_now, cell('left'), cell('right')))

            rows.append({
                'step': step, 'x': round(x_now, 3),
                'left_mean': round(reading['left'], 4), 'right_mean': round(reading['right'], 4),
                'left_dev': round(deviation['left'], 4), 'right_dev': round(deviation['right'], 4),
                'left_inc': round(increment['left'], 4), 'right_inc': round(increment['right'], 4),
                'left_ratio': None if ratio['left'] is None else round(ratio['left'], 3),
                'right_ratio': None if ratio['right'] is None else round(ratio['right'], 3),
                'left_readings': ";".join("%.4f" % v for v in left),
                'right_readings': ";".join("%.4f" % v for v in right),
            })

            previous_dev = dict(deviation)
            previous_inc = dict(increment)

            over = [s for s in deviation if abs(deviation[s]) > args.hard_abort]
            if over:
                stop_reason = ("backstop: %s deviated %.1f, over %.0f"
                               % (", ".join(over),
                                  max(abs(deviation[s]) for s in over), args.hard_abort))
                print("    !! %s - stopping" % stop_reason)
                break

            jumped = None
            for side in ('left', 'right'):
                if ratio[side] is not None and ratio[side] >= args.jump_factor:
                    jump_streak[side] += 1
                    if jump_streak[side] >= args.jump_consecutive:
                        jumped = side
                else:
                    jump_streak[side] = 0
            if jumped:
                stop_reason = ("%s cell increment jumped >= %.1fx for %d steps running"
                               % (jumped, args.jump_factor, args.jump_consecutive))
                print("    -> %s - stopping" % stop_reason)
                break

        print("\n--- Retracting to the right ---")
        ber.moveAxis('X', start_x)
        back_left, back_right = readBoth(ber, args.readings_per_step)
        returned = {'left': statistics.mean(back_left) - baseline['left'][0],
                    'right': statistics.mean(back_right) - baseline['right'][0]}
        print("    back at X=%.3f; readings now deviate left %+.3f, right %+.3f"
              % (ber.getPosition('X'), returned['left'], returned['right']))
        ber.moveAxis('Z', 0)

        print("\n--- Outcome ---")
        print("  stopped because: %s" % stop_reason)
        if rows:
            results.check("the run produced usable data", True, "%d steps recorded" % len(rows))
            # Both cells, not just the right one: single steps over the factor do
            # occur in pure drift - the left cell reached 2.32 during the control
            # run - which is exactly why the trigger needs several in a row.
            peak = {}
            for side in ('left', 'right'):
                seen = [r['%s_ratio' % side] for r in rows if r['%s_ratio' % side] is not None]
                peak[side] = max(seen) if seen else 0.0
            worst = max(peak.values())
            results.check("no abrupt change was seen (drift only)",
                          worst < args.jump_factor,
                          "largest increment ratio: left %.2f, right %.2f, against a %.1f "
                          "trigger (%d in a row needed)"
                          % (peak['left'], peak['right'], args.jump_factor,
                             args.jump_consecutive))
            for side in ('left', 'right'):
                far = rows[-1]['%s_dev' % side]
                reversible = abs(returned[side]) < abs(far) / 2.0 if far else None
                results.check("%s cell came back towards baseline on retract" % side,
                              bool(reversible),
                              "ended %+.3f at the far point, %+.3f back at the start"
                              % (far, returned[side]))

    path = os.path.join(REPORT_DIR, '%s_side_load%s.csv'
                        % (timestamp(), '_control' if control else ''))
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'step', 'x', 'left_mean', 'right_mean', 'left_dev', 'right_dev',
            'left_inc', 'right_inc', 'left_ratio', 'right_ratio',
            'left_readings', 'right_readings'])
        writer.writeheader()
        writer.writerows(rows)
    print("\nData: %s" % path)
    print("Stop reason: %s" % stop_reason)
    return results.report()


if __name__ == '__main__':
    sys.exit(main())

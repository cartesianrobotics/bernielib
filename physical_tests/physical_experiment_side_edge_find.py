"""
Physical experiment: find rack edges sideways, and check them against Z-tapping.

An earlier experiment established two things. The load cells see a sideways touch
very clearly - one increment 93x the previous, against a drift maximum of 2.32 -
and both cells also ramp steadily as the carriage moves, whether or not anything
is being touched, because the carriage geometry changes with position. That drift
is what makes a naive threshold useless.

Each side is measured like this:

  1. Walk the positions ABOVE the rack, where contact is impossible, recording
     both cells at each. That is the background.
  2. Return, drop to the working height, walk the same positions again, and
     subtract the background reading for the matching position from each. What
     is left should be flat until something is actually touched.
  3. Stop at the first abrupt spike - an increment --jump-factor times the
     previous, or a corrected reading over --abs-cutoff.
  4. Work out where contact begins to 0.1 mm: retreat in 0.1 mm steps until the
     spike has all but gone, back off a couple more, and advance again until it
     returns. Repeat, so the crossing is measured several times independently.
  5. Compare against the edge the existing Z-tapping calibration found, read out
     of the newest report in calibration_reports/.

SIDES. 'right' and 'left' are the small-X and large-X edges; 'front' and 'back'
are the small-Y and large-Y edges. Y edges are approached along the same X line
that the Z-tapping calibration uses for them (centre plus x_shift_for_y), and at
the same heights as the X work, so the two methods measure the same thing.

Several sides can be given at once. Between them the pipette lifts to the safe
height - the rack top less --safe-height, the same 20 mm clearance moveToWell()
uses - so it never crosses the deck at working depth. Going all the way to Z=0
buys nothing over that and costs a full Z traverse each way. Within a side there
is no lift at all between the background and working passes: the background pass
has just traversed the whole range above the plane, so returning along the axis
at that height is already known clear.

    python physical_tests/physical_experiment_side_edge_find.py
    python physical_tests/physical_experiment_side_edge_find.py --side front,back --move-the-robot
    python physical_tests/physical_experiment_side_edge_find.py --side right,left,front,back --move-the-robot

When both sides of an axis are measured, the summary compares the centre and
span the two methods imply, which is where a wall that is not vertical shows up:
measuring 5 mm below the top plane found the samples body 1.23 mm wider than
Z-tapping did, and put its centre 0.52 mm off.

A note on the jump rule. Contact is a step change, not exponential growth: one
huge increment, then increments that stay large but stop growing, with ratios
back near 1. So the trigger is a SINGLE large ratio, not several in a row.

ON FORCE. The coarse approach stops at the first spike and the fine steps are
0.1 mm, so contact is re-made gently. Neither substitutes for watching the
machine: the cells cannot report a force they do not feel.

Part of BernieLib.
"""

import csv
import glob
import json
import os
import statistics
import sys

from harness import parseArgs, requireRepoRootCwd, physical_test, checklist
from calibration_common import PIPETTE_END_DIAMETER, timestamp


REPORT_DIR = 'experiment_reports'
# Never travel closer than this to either end of an axis.
EDGE_MARGIN = 1.0

# Usable travel, short of what robot.json's x_max claims. The carriage fouls the
# far end of X well before 189: a left-edge approach starting at 172.90 lost
# about 0.8 mm of steps on the way, and since every later position is measured
# from there, the whole run read high. It showed up as the left edge apparently
# disagreeing with Z-tapping by 1.100 mm, which looked like a real feature on the
# wall and was not. Starting at 171.40 gave 168.900, and 170.40 gave 168.967 -
# converged, so the interference is gone by 171.40 and that is the cap.
# See experiment_reports/README.md.
USABLE_MAX = {'X': 171.4}
# Increments below this are too small for their ratio to mean anything.
INCREMENT_FLOOR = 0.4
# Steps used to establish how flat the corrected signal is before anything is
# touched. Detection is then scaled to that band rather than to a fixed number.
BAND_STEPS = 4

# side -> (axis, approach). approach +1 means the low-coordinate edge, reached by
# moving in the positive direction; -1 means the high-coordinate edge.
SIDES = {
    'right': ('X', 1),
    'left': ('X', -1),
    'front': ('Y', 1),
    'back': ('Y', -1),
}


def readBoth(ber, times):
    left, right = [], []
    for _ in range(times):
        left.append(ber.readLeftLoad())
        right.append(ber.readRightLoad())
    return left, right


def measure(ber, times):
    left, right = readBoth(ber, times)
    return {'left': statistics.mean(left), 'right': statistics.mean(right)}


def takeBaseline(ber, times=10):
    ber.tareAll()
    left, right = readBoth(ber, times)
    return {'left': (statistics.mean(left), statistics.stdev(left)),
            'right': (statistics.mean(right), statistics.stdev(right))}


def deviation(reading, baseline):
    return {s: reading[s] - baseline[s][0] for s in reading}


def backgroundAt(points, position):
    """
    Background deviation at an arbitrary position, linearly interpolated between
    the sampled ones. The drift is smooth and near-linear, so this is sound
    between samples, and it lets the 0.1 mm work reuse a 0.5 mm background.

    Sorted first: high-side scans run with the coordinate decreasing, so the
    points arrive in descending order and every comparison would be backwards.
    """
    if not points:
        return {'left': 0.0, 'right': 0.0}
    points = sorted(points, key=lambda point: point[0])
    if position <= points[0][0]:
        return dict(points[0][1])
    if position >= points[-1][0]:
        return dict(points[-1][1])
    for i in range(1, len(points)):
        p0, d0 = points[i - 1]
        p1, d1 = points[i]
        if p0 <= position <= p1:
            span = p1 - p0
            t = 0.0 if span == 0 else (position - p0) / span
            return {s: d0[s] + t * (d1[s] - d0[s]) for s in d0}
    return dict(points[-1][1])


def signalOf(corrected):
    """One number for 'how much is being touched', taking whichever cell says more."""
    return max(abs(corrected['left']), abs(corrected['right']))


def zTappingEdge(rack_name, axis, approach):
    """
    The edge the existing calibration found on this side, from the newest report.
    Its scans are recorded with the direction they travelled, which is the
    opposite of our approach direction.
    Returns (value, source) or (None, why not).
    """
    wanted = -approach
    files = sorted(glob.glob(os.path.join('calibration_reports', '*_tube_racks.json')))
    if not files:
        return None, "no tube rack calibration report found"
    try:
        data = json.load(open(files[-1]))
        edges = data['found'][rack_name]['edges']
    except (IOError, ValueError, KeyError):
        return None, "newest report has no edges for %s" % rack_name
    for edge_axis, direction, coordinate in edges:
        if edge_axis.upper() == axis and direction * wanted > 0 and coordinate is not None:
            return coordinate, os.path.basename(files[-1])
    return None, "no matching %s edge in %s" % (axis, os.path.basename(files[-1]))


def addArgs(parser):
    parser.add_argument('--rack', default='samples')
    parser.add_argument('--side', default='right',
                        help="Comma separated: right, left (X edges), front, back (Y "
                             "edges). Default: right.")
    parser.add_argument('--depth', type=float, default=5.0,
                        help="Working height, mm below the rack top plane. Default: 5.")
    parser.add_argument('--background-height', type=float, default=20.0,
                        help="How far ABOVE the top plane to take the background. "
                             "Default: 20.")
    parser.add_argument('--safe-height', type=float, default=20.0,
                        help="Travel height between sides, mm above the rack top plane. "
                             "Matches moveToWell()'s save_height convention. At 20 this "
                             "clears the tips rack - the tallest thing on the deck - by "
                             "15 mm, and it is the height the background pass already "
                             "traverses, so every run demonstrates it is clear. "
                             "Default: 20.")
    parser.add_argument('--steps', type=int, default=14)
    parser.add_argument('--step-size', type=float, default=0.5)
    parser.add_argument('--readings-per-step', type=int, default=3)
    parser.add_argument('--band-steps', type=int, default=BAND_STEPS,
                        help="Steps used to measure the flat band before detection "
                             "starts. Every one of them must be clear of the wall: a "
                             "step taken in contact inflates the band and raises the "
                             "threshold above the very signal it should catch. Shorten "
                             "it when the run-up is short. Default: %d." % BAND_STEPS)
    parser.add_argument('--band-factor', type=float, default=3.0,
                        help="Contact is called when the corrected signal exceeds this "
                             "many times the flat band measured over the first few steps. "
                             "Pre-contact signal never exceeded 1.6 on any side; first "
                             "contact was always at least 4.4. Default: 3.")
    parser.add_argument('--band-floor', type=float, default=3.0,
                        help="...but never trigger below this absolute value. Default: 3.")
    parser.add_argument('--jump-factor', type=float, default=5.0,
                        help="Secondary trigger: a single increment this many times the "
                             "previous one. Kept because it catches a step change even "
                             "when the band is unusually wide, but it is no longer the "
                             "primary rule - it missed the back Y edge, where the "
                             "decisive ratio was suppressed by INCREMENT_FLOOR. "
                             "Default: 5.")
    parser.add_argument('--abs-cutoff', type=float, default=70.0,
                        help="Force backstop, not a detector. Contact magnitude ranged "
                             "from 11 to 91 across four edges, so no fixed value can "
                             "detect it; three sides in four never reach this. "
                             "Default: 70.")
    parser.add_argument('--fine-step', type=float, default=0.1)
    parser.add_argument('--fine-fraction', type=float, default=0.10,
                        help="Contact is considered gone once the corrected signal falls "
                             "to this fraction of the spike. Default: 0.10.")
    parser.add_argument('--fine-floor', type=float, default=5.0,
                        help="...but never below this absolute value. Default: 5.")
    parser.add_argument('--fine-cycles', type=int, default=3,
                        help="Independent determinations of the crossing. Default: 3.")
    parser.add_argument('--fine-backoff-steps', type=int, default=2)
    parser.add_argument('--fine-max-steps', type=int, default=40,
                        help="Bound on fine steps in one direction, so a cycle that never "
                             "finds its crossing cannot wander. Default: 40.")
    parser.add_argument('--fine-abort', type=float, default=120.0,
                        help="Abandon the fine work if the corrected signal exceeds this.")


def planFor(side, rack, limits, args):
    """Everything geometric about one side, worked out before anything moves."""
    axis, approach = SIDES[side]
    center_x, center_y = rack.getCenterXY()
    max_x, max_y, max_z = rack.getRackSize()
    y_shift_for_x, x_shift_for_y = rack.getXYCalibrationShift()

    if axis == 'X':
        centre, size, limit = center_x, max_x, limits['X']
        # Same line the Z-tapping calibration uses for its X edge scans.
        cross_axis, cross_value = 'Y', center_y + y_shift_for_x
    else:
        centre, size, limit = center_y, max_y, limits['Y']
        cross_axis, cross_value = 'X', center_x + x_shift_for_y

    edge = centre - approach * size / 2.0
    contact = edge - approach * PIPETTE_END_DIAMETER / 2.0
    start = edge - approach * args.steps * args.step_size
    # The upper cap is the usable travel where one is recorded, otherwise the
    # stored axis limit. The coarse pass stops at contact, so capping the start
    # only shortens the run-up; it does not push the far end into the rack.
    upper = USABLE_MAX.get(axis, limit - EDGE_MARGIN)
    start = max(EDGE_MARGIN, min(upper, start))
    positions = [round(start + approach * i * args.step_size, 3)
                 for i in range(1, args.steps + 1)]
    ztap, ztap_source = zTappingEdge(args.rack, axis, approach)

    return {'side': side, 'axis': axis, 'approach': approach, 'edge': edge,
            'contact': contact, 'start': start, 'positions': positions,
            'cross_axis': cross_axis, 'cross_value': cross_value,
            'ztap': ztap, 'ztap_source': ztap_source}


def goTo(ber, plan, coordinate, target_z, safe_z):
    """
    Place both axes, then drop to target_z, travelling at safe_z.

    safe_z rather than Z=0: going all the way to the home height costs a full
    Z traverse each way and buys nothing, since safe_z already clears every rack
    on the deck.
    """
    ber.moveAxis('Z', safe_z)
    if plan['axis'] == 'X':
        ber.move(coordinate, plan['cross_value'], safe_z, z_first=False)
    else:
        ber.move(plan['cross_value'], coordinate, safe_z, z_first=False)
    if abs(target_z - safe_z) > 1e-6:
        ber.moveAxis('Z', target_z)


def runSide(ber, plan, args, working_z, background_z, safe_z, logRow, results):
    """Background pass, coarse approach and fine crossings for one side."""
    side, axis, approach = plan['side'], plan['axis'], plan['approach']
    label = "%s (%s edge)" % (side, axis)
    outcome = {'side': side, 'axis': axis, 'contacts': [], 'releases': [],
               'mean': None, 'ztap': plan['ztap'], 'aborted': None}

    print("\n########## %s ##########" % label.upper())

    print("\n=== 1. Background, %.1f mm above the plane ===" % args.background_height)
    goTo(ber, plan, plan['start'], background_z, safe_z)
    base_bg = takeBaseline(ber)
    print("    baseline left %+.3f (sd %.3f), right %+.3f (sd %.3f)"
          % (base_bg['left'][0], base_bg['left'][1],
             base_bg['right'][0], base_bg['right'][1]))
    background = []
    for position in plan['positions']:
        ber.moveAxis(axis, position)
        reading = measure(ber, args.readings_per_step)
        dev = deviation(reading, base_bg)
        background.append((position, dev))
        logRow(side, 'background', position, reading, dev, None, None)
    print("    %d points, drift spans left %+.3f, right %+.3f"
          % (len(background), background[-1][1]['left'], background[-1][1]['right']))

    print("\n=== 2. Working pass, %.1f mm below the plane, background subtracted ==="
          % args.depth)
    # No lift: the background pass has just traversed this whole range above the
    # plane, so returning along the axis at that height is already known clear.
    # Only then drop to the working height, at the start point, off the rack.
    ber.moveAxis(plan['axis'], plan['start'])
    ber.moveAxis('Z', working_z)
    base_work = takeBaseline(ber)
    print("    %-9s %-24s %-24s %-9s %s"
          % (axis, "left dev / bg / corr", "right dev / bg / corr", "signal", "ratio"))

    spike_at = spike_signal = None
    previous_signal, previous_increment = 0.0, None
    band_samples = []
    band_threshold = None
    for step_number, position in enumerate(plan['positions'], start=1):
        ber.moveAxis(axis, position)
        reading = measure(ber, args.readings_per_step)
        dev = deviation(reading, base_work)
        bg = backgroundAt(background, position)
        corrected = {s: dev[s] - bg[s] for s in dev}
        signal = signalOf(corrected)
        increment = signal - previous_signal
        ratio = None
        if previous_increment is not None and abs(previous_increment) >= INCREMENT_FLOOR:
            ratio = abs(increment) / abs(previous_increment)
        print("    %-9.3f %+7.3f %+7.3f %+7.3f  %+7.3f %+7.3f %+7.3f  %-9.3f %s"
              % (position, dev['left'], bg['left'], corrected['left'],
                 dev['right'], bg['right'], corrected['right'],
                 signal, "  -  " if ratio is None else "%.2f" % ratio))
        logRow(side, 'approach', position, reading, dev, bg, corrected)

        # The first few steps establish how flat "untouched" looks here, and
        # detection is scaled to that. A fixed number cannot work: contact
        # measured 11 on one edge and 91 on another.
        if step_number <= args.band_steps:
            band_samples.append(signal)
            if step_number == args.band_steps:
                band_threshold = max(args.band_floor, args.band_factor * max(band_samples))
                print("    flat band %.3f over %d steps -> contact above %.2f"
                      % (max(band_samples), args.band_steps, band_threshold))
            previous_signal, previous_increment = signal, increment
            continue

        if signal >= args.abs_cutoff:
            spike_at, spike_signal = position, signal
            print("    -> corrected signal %.1f over the %.0f force backstop"
                  % (signal, args.abs_cutoff))
            break
        if band_threshold is not None and signal >= band_threshold:
            spike_at, spike_signal = position, signal
            print("    -> corrected signal %.1f is over the %.2f band threshold: contact"
                  % (signal, band_threshold))
            break
        if ratio is not None and ratio >= args.jump_factor:
            spike_at, spike_signal = position, signal
            print("    -> increment jumped %.1fx: contact" % ratio)
            break
        previous_signal, previous_increment = signal, increment

    if spike_at is None:
        results.check("%s: contact detected" % label, False,
                      "walked to %.3f without a spike" % plan['positions'][-1])
        outcome['aborted'] = 'no contact'
        ber.moveAxis(axis, plan['start'])
        ber.moveAxis('Z', safe_z)
        return outcome

    results.check("%s: contact detected" % label, True,
                  "spike at %.3f, corrected signal %.1f" % (spike_at, spike_signal))
    # The same criterion that called contact decides whether it is still there.
    # Deriving this from the spike magnitude instead would break the moment the
    # coarse pass stops early: 10% of a 4.4 spike is below the noise, and the
    # old floor of 5.0 sat above the contact signal itself, so the fine phase
    # could never have re-contacted.
    if band_threshold is not None:
        threshold = band_threshold
    else:
        threshold = max(args.fine_fraction * spike_signal, args.fine_floor)
    print("    contact counts as present above a corrected signal of %.2f" % threshold)

    def signalAt(position):
        ber.moveAxis(axis, position)
        reading = measure(ber, args.readings_per_step)
        dev = deviation(reading, base_work)
        bg = backgroundAt(background, position)
        corrected = {s: dev[s] - bg[s] for s in dev}
        return signalOf(corrected), reading, dev, bg, corrected

    print("\n=== 3. Fine crossings, %.2f mm steps ===" % args.fine_step)
    position = spike_at
    for cycle in range(1, args.fine_cycles + 1):
        release = None
        for _ in range(args.fine_max_steps):
            position = round(position - approach * args.fine_step, 3)
            signal, reading, dev, bg, corrected = signalAt(position)
            logRow(side, 'retreat%d' % cycle, position, reading, dev, bg, corrected)
            if signal <= threshold:
                release = position
                break
        if release is None:
            outcome['aborted'] = "cycle %d never released" % cycle
            break
        outcome['releases'].append(release)

        position = round(position - approach * args.fine_backoff_steps * args.fine_step, 3)
        ber.moveAxis(axis, position)

        contact = None
        for _ in range(args.fine_max_steps):
            position = round(position + approach * args.fine_step, 3)
            signal, reading, dev, bg, corrected = signalAt(position)
            logRow(side, 'advance%d' % cycle, position, reading, dev, bg, corrected)
            if signal > args.fine_abort:
                outcome['aborted'] = "signal %.1f over the fine abort" % signal
                break
            if signal >= threshold:
                contact = position
                break
        if outcome['aborted']:
            break
        if contact is None:
            outcome['aborted'] = "cycle %d never re-contacted" % cycle
            break
        outcome['contacts'].append(contact)
        print("    cycle %d: released at %.3f, contacted at %.3f" % (cycle, release, contact))

    while True:
        signal, reading, dev, bg, corrected = signalAt(position)
        logRow(side, 'final_retreat', position, reading, dev, bg, corrected)
        if signal <= threshold or (position - plan['start']) * approach <= 0:
            break
        position = round(position - approach * args.fine_step, 3)
    ber.moveAxis(axis, plan['start'])
    ber.moveAxis('Z', safe_z)    # clear of every rack, ready to travel
    print("    retreated clear, lifted to the safe height Z=%.2f" % safe_z)

    if outcome['aborted']:
        print("    fine work stopped early: %s" % outcome['aborted'])
    if outcome['contacts']:
        outcome['mean'] = statistics.mean(outcome['contacts'])
        sd = statistics.stdev(outcome['contacts']) if len(outcome['contacts']) > 1 else 0.0
        results.check("%s: crossings agree with each other" % label, sd <= 0.15,
                      "mean %.3f, spread %.3f over %d"
                      % (outcome['mean'], sd, len(outcome['contacts'])))
        if plan['ztap'] is not None:
            difference = outcome['mean'] - plan['ztap']
            outcome['difference'] = difference
            results.check("%s: agrees with Z-tapping to within 0.5 mm" % label,
                          abs(difference) <= 0.5,
                          "sideways %.3f, Z-tapping %.3f, difference %+.3f"
                          % (outcome['mean'], plan['ztap'], difference))
    return outcome


def main():
    args = parseArgs(__doc__, extra=addArgs)
    requireRepoRootCwd()

    import bernielib as bl

    sides = [s.strip() for s in args.side.split(',') if s.strip()]
    unknown = [s for s in sides if s not in SIDES]
    if unknown:
        sys.exit("Unknown side(s): %s. Choose from %s." % (unknown, sorted(SIDES)))

    rack = bl.rack(args.rack)
    top_plane = rack.getZ()
    working_z = top_plane + args.depth
    background_z = top_plane - args.background_height
    safe_z = top_plane - args.safe_height
    robot_settings = bl.data('robot')
    limits = {'X': robot_settings._getSetting('x_max'),
              'Y': robot_settings._getSetting('y_max')}

    plans = [planFor(side, rack, limits, args) for side in sides]

    print("Plan: %s, top plane Z %.2f" % (args.rack, top_plane))
    print("  background at Z %.2f, working at Z %.2f  (%.1f above / %.1f below the plane)"
          % (background_z, working_z, args.background_height, args.depth))
    print("  spike when increment >= %.1fx previous, or corrected >= %.0f; then %d cycles "
          "of %.2f mm" % (args.jump_factor, args.abs_cutoff, args.fine_cycles, args.fine_step))
    for plan in plans:
        print("  %-6s %s edge, nominal %7.2f, touch near %7.2f, walk %7.2f -> %7.2f "
              "along %s at %s=%.2f"
              % (plan['side'], plan['axis'], plan['edge'], plan['contact'],
                 plan['positions'][0], plan['positions'][-1], plan['axis'],
                 plan['cross_axis'], plan['cross_value']))
        if plan['ztap'] is None:
            print("         compare against: UNAVAILABLE - %s" % plan['ztap_source'])
        else:
            print("         compare against: Z-tapping %.3f (%s)"
                  % (plan['ztap'], plan['ztap_source']))
    print("  travel between sides happens at the safe height Z=%.2f" % safe_z)

    if not args.confirmed:
        print("\nNothing moved. Re-run with --move-the-robot to perform the experiment.")
        return 0

    os.makedirs(REPORT_DIR, exist_ok=True)
    rows = []
    results = checklist()

    def logRow(side, phase, position, reading, dev, background, corrected):
        rows.append({
            'side': side, 'phase': phase, 'position': round(position, 3),
            'left_raw': round(reading['left'], 4), 'right_raw': round(reading['right'], 4),
            'left_dev': round(dev['left'], 4), 'right_dev': round(dev['right'], 4),
            'left_bg': None if background is None else round(background['left'], 4),
            'right_bg': None if background is None else round(background['right'], 4),
            'left_corr': None if corrected is None else round(corrected['left'], 4),
            'right_corr': None if corrected is None else round(corrected['right'], 4),
            'signal': None if corrected is None else round(signalOf(corrected), 4),
        })

    outcomes = []
    with physical_test('sideways edge finding') as ber:
        for plan in plans:
            outcomes.append(runSide(ber, plan, args, working_z, background_z, safe_z,
                                    logRow, results))

    print("\n########## SUMMARY ##########")
    print("  %-7s %-5s %10s %10s %10s" % ("side", "axis", "sideways", "Z-tapping", "difference"))
    for outcome in outcomes:
        mean = "  -  " if outcome['mean'] is None else "%10.3f" % outcome['mean']
        ztap = "  -  " if outcome['ztap'] is None else "%10.3f" % outcome['ztap']
        diff = ("%10.3f" % outcome['difference']) if outcome.get('difference') is not None else "  -  "
        print("  %-7s %-5s %s %s %s" % (outcome['side'], outcome['axis'], mean, ztap, diff))

    # With both sides of an axis, the centre and span each method implies can be
    # compared. A wall that is not vertical shows up as a wider span; walls that
    # differ from each other show up as a shifted centre.
    for axis in ('X', 'Y'):
        pair = [o for o in outcomes if o['axis'] == axis and o['mean'] is not None]
        if len(pair) != 2 or any(o['ztap'] is None for o in pair):
            continue
        sideways = sorted(o['mean'] for o in pair)
        tapping = sorted(o['ztap'] for o in pair)
        print("\n  %s axis, both sides measured:" % axis)
        print("    %-10s %10s %10s" % ("", "centre", "span"))
        print("    %-10s %10.3f %10.3f" % ("sideways", sum(sideways) / 2, sideways[1] - sideways[0]))
        print("    %-10s %10.3f %10.3f" % ("Z-tapping", sum(tapping) / 2, tapping[1] - tapping[0]))
        print("    %-10s %10.3f %10.3f" % ("difference",
                                           sum(sideways) / 2 - sum(tapping) / 2,
                                           (sideways[1] - sideways[0]) - (tapping[1] - tapping[0])))

    path = os.path.join(REPORT_DIR, '%s_side_edge_find.csv' % timestamp())
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'side', 'phase', 'position', 'left_raw', 'right_raw', 'left_dev', 'right_dev',
            'left_bg', 'right_bg', 'left_corr', 'right_corr', 'signal'])
        writer.writeheader()
        writer.writerows(rows)
    print("\nData: %s" % path)
    return results.report()


if __name__ == '__main__':
    sys.exit(main())

"""
Physical experiment for descending coordinated wall washes in sample position 0.

This file is inert unless --move-the-robot is provided. The gated run homes,
picks the next tip, transfers 30 uL of yellow liquid from reagent position 2 to
the empty tube, performs three aspirate/descending-wall-wash cycles, removes the
liquid to reagent position 1, drops the tip into tip waste, and homes again.

Run from the repository root with the project Python. See the experiment README
for deck preparation and the exact command.
"""

import argparse
import datetime
import math
import os
import shutil
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import bernielib as bl  # noqa: E402


EXPERIMENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIRM_FLAG = '--move-the-robot'
TUBE_COLUMN = 1
TUBE_ROW = 0
REAGENT_COLUMN = 0
YELLOW_REAGENT_POSITION = 2
LIQUID_WASTE_POSITION = 1
WASH_VOLUME_UL = 30.0
YELLOW_STARTING_VOLUME_UL = 25000.0
TIP_CLEARANCE_LIFT_MM = 30.0
WALL_WASH_REPETITIONS = 3
DEFAULT_FEED_RATE = 600.0
CONFIG_FILES = (
    'robot.json',
    'samples.json',
    'waste.json',
    'tips.json',
    'reagents.json',
    'eppendorf.json',
    '25mL.json',
)
CODE_FILES = ('bernielib.py', 'samples.py', 'general.py')

# Approach the wide end of the taper without dispensing. The three queued
# segments then move downward and inward while expelling 1/3 of the liquid each.
WALL_WASH_START = (3.000, 24.0)
WALL_WASH_PATH = (
    (3.000, 28.0),
    (2.371, 32.0),
    (1.742, 36.0),
)


def parseArgs(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(CONFIRM_FLAG, action='store_true', dest='confirmed',
                        help='Required to connect and move. Stand at the robot.')
    parser.add_argument('--feed-rate', type=float, default=DEFAULT_FEED_RATE,
                        help='Combined G1 feed rate. Default: %(default)s.')
    return parser.parse_args(argv)


def requireRepoRootCwd():
    required = ('bernielib.py',) + CONFIG_FILES
    missing = [path for path in required if not os.path.isfile(path)]
    if missing:
        sys.exit('Run this experiment from the repository root. Missing: %s\n    cd %s'
                 % (', '.join(missing), REPO_ROOT))


def snapshotRunInputs(run_id):
    """Freeze settings and local modules before opening serial ports."""
    config_destination = os.path.join(EXPERIMENT_DIR, 'configs', run_id)
    code_destination = os.path.join(EXPERIMENT_DIR, 'scripts', 'snapshots', run_id)
    os.makedirs(config_destination)
    os.makedirs(code_destination)
    for filename in CONFIG_FILES:
        shutil.copy2(os.path.join(REPO_ROOT, filename),
                     os.path.join(config_destination, filename))
    for filename in CODE_FILES:
        shutil.copy2(os.path.join(REPO_ROOT, filename),
                     os.path.join(code_destination, filename))
    shutil.copy2(__file__, os.path.join(code_destination, os.path.basename(__file__)))
    return config_destination, code_destination


def makeSamples(run_id, ber):
    """Create isolated state for the empty tube, yellow source, and liquid waste."""
    def stateName(label):
        state_path = os.path.join(EXPERIMENT_DIR, 'data', label + '_' + run_id)
        return os.path.relpath(state_path, REPO_ROOT)

    tube = bl.createSample('eppendorf', stateName('wall_wash_sample'),
                           ber.samples_rack, pos_col=TUBE_COLUMN,
                           pos_row=TUBE_ROW, volume=0, purge=True)
    yellow = bl.createSample('25mL', stateName('yellow_reagent'),
                             ber.reagents_rack, pos_col=REAGENT_COLUMN,
                             pos_row=YELLOW_REAGENT_POSITION,
                             volume=YELLOW_STARTING_VOLUME_UL, purge=True)
    liquid_waste = bl.createSample('25mL', stateName('liquid_waste'),
                                   ber.reagents_rack, pos_col=REAGENT_COLUMN,
                                   pos_row=LIQUID_WASTE_POSITION,
                                   volume=0, purge=True)
    return tube, yellow, liquid_waste


def coordinatedWallWash(ber, sample, volume=WASH_VOLUME_UL,
                        feed_rate=DEFAULT_FEED_RATE):
    """Approach above the pellet, then queue three descending dispense segments."""
    x_center, y_center = sample.getCenterXY()
    z_top = sample.getSampleTopAbsZ(added_length=ber._calcExtraLength())
    last_index = len(WALL_WASH_PATH) - 1

    # Uptake ends near the tube bottom. First rise at the centre, then move to
    # the wide upper wall. Neither approach movement changes A, so the tip does
    # not scrape upward along the pellet-bearing taper and does not dispense yet.
    start_x_offset, start_z_from_top = WALL_WASH_START
    print('  approach: rise at centre to Z=%0.3f, then move sideways to X=%0.3f'
          % (z_top + start_z_from_top, x_center + start_x_offset))
    ber.moveAxis('Z', z_top + start_z_from_top)
    ber.moveXY(x_center + start_x_offset, y_center)

    print('  wash: three queued downward G1 XYZ/A blocks')
    for index, (x_offset, z_from_top) in enumerate(WALL_WASH_PATH):
        dispense_volume = volume * (index + 1) / len(WALL_WASH_PATH)
        plunger_position = ber.calcPipettePositionFromVolume(dispense_volume)
        final_waypoint = index == last_index
        print('  %d: X=%0.3f Y=%0.3f Z=%0.3f A=%0.3f (%0.1f uL)%s'
              % (index + 1, x_center + x_offset, y_center,
                 z_top + z_from_top, plunger_position, dispense_volume,
                 ' then M400' if final_waypoint else ''))
        ber.moveCoordinated(x=x_center + x_offset,
                            y=y_center,
                            z=z_top + z_from_top,
                            a=plunger_position,
                            speed=feed_rate,
                            wait=final_waypoint)

    # uptakeLiquid() recorded the tube as empty; the coordinated path returned
    # the same liquid, so restore the model only after the final M400 completed.
    sample.setVolume(volume)
    # Leave the wall inward, not upward, then retract at the centre. Besides
    # protecting the pellet, this gets the tip out of the liquid before the next
    # uptake pre-positions its plunger (which would otherwise blow air at depth).
    ber.moveXY(x_center, y_center)
    ber.moveAxis('Z', z_top + start_z_from_top)


def executeExperiment(ber, sample, yellow, liquid_waste, feed_rate, state=None):
    """Execute the requested physical sequence on an already connected robot."""
    print('\n--- Establishing absolute coordinates: home ---')
    ber.home()

    print('\n--- Picking up the next available tip ---')
    if state is not None:
        # Set immediately before pickup: if the call raises after physical
        # engagement, exception cleanup must assume a tip is on the nozzle.
        state['tip_may_be_attached'] = True
    tip_column, tip_row = ber.pickUpNextTip()
    print('  picked software-inventory tip [%d, %d]' % (tip_column, tip_row))

    print('\n--- Raising an additional 30 mm for 25 mL bottle clearance ---')
    ber.moveAxisDelta('Z', -TIP_CLEARANCE_LIFT_MM)

    print('\n--- Transferring 30 uL yellow liquid: reagent position 2 -> tube 0 ---')
    ber.transferLiquid(yellow, sample, WASH_VOLUME_UL,
                       touch_wall=False, safe_z=50)

    for repetition in range(WALL_WASH_REPETITIONS):
        print('\n--- Tapered wall wash %d of %d: aspirate, approach high, dispense down ---'
              % (repetition + 1, WALL_WASH_REPETITIONS))
        ber.uptakeLiquid(sample, WASH_VOLUME_UL, lag_vol=5)
        coordinatedWallWash(ber, sample, WASH_VOLUME_UL, feed_rate)

    print('\n--- Removing all liquid: tube 0 -> liquid waste at reagent position 1 ---')
    initial_waste_volume = liquid_waste.getVolume()
    ber.transferLiquid(sample, liquid_waste, WASH_VOLUME_UL,
                       dry_tube=True, touch_wall=False, safe_z=50)
    # transferLiquid includes aspirated air in its dispense-volume bookkeeping.
    # Only 30 uL of liquid was added to the waste tube, so keep its model physical.
    liquid_waste.setVolume(initial_waste_volume + WASH_VOLUME_UL)

    print('\n--- Dropping the tip into tip waste ---')
    ber.dumpTipToWaste()
    if state is not None:
        state['tip_may_be_attached'] = False

    print('\n--- Final home ---')
    ber.home()


def printDryPlan(feed_rate):
    print('DRY PLAN ONLY -- no robot object was created and no serial port was opened.')
    print('Would home; pickUpNextTip(); raise Z another %.1f mm; transfer %.1f uL'
          % (TIP_CLEARANCE_LIFT_MM, WASH_VOLUME_UL))
    print('from yellow reagent [0,2] to empty sample [1,0]; perform %d aspirate/'
          % WALL_WASH_REPETITIONS)
    print('descending three-segment wall washes at F%s; dry sample [1,0] into'
          % feed_rate)
    print('liquid waste [0,1]; dumpTipToWaste(); home.')
    print('Pass %s only while standing at the prepared robot.' % CONFIRM_FLAG)


def main(argv=None):
    args = parseArgs(argv)
    requireRepoRootCwd()
    if not args.confirmed:
        printDryPlan(args.feed_rate)
        return 0
    if not math.isfinite(args.feed_rate) or args.feed_rate <= 0:
        sys.exit('--feed-rate must be a positive finite number.')

    run_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    config_dir, code_dir = snapshotRunInputs(run_id)
    print('Settings snapshot: %s' % config_dir)
    print('Code snapshot:     %s' % code_dir)

    ber = None
    state = {'tip_may_be_attached': False}
    completed = False
    try:
        print('Connecting (BernieLib will scan serial ports)...')
        ber = bl.robot()
        sample, yellow, liquid_waste = makeSamples(run_id, ber)

        executeExperiment(ber, sample, yellow, liquid_waste,
                          args.feed_rate, state=state)
        completed = True
        print('\nExperiment sequence completed.')
        return 0
    finally:
        if ber is not None:
            try:
                if not completed:
                    print('\n--- Exception cleanup ---')
                    if state['tip_may_be_attached']:
                        print('Assuming a tip may be attached; discarding to waste.')
                        ber.tip_attached = 1
                        ber.dumpTipToWaste()
                    ber.home()
                ber.powerStepperOff()
            finally:
                ber.close()
                print('Ports closed.')


if __name__ == '__main__':
    sys.exit(main())

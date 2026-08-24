"""
Physical experiment for a continuous, coordinated wall wash in sample position 0.

This file is inert unless --move-the-robot is provided. The gated run homes,
picks the next tip, aspirates 30 uL of water from position 0, queues four combined
XYZ/A G1 moves, drops the tip into the waste, and homes again.

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
WASH_VOLUME_UL = 30.0
DEFAULT_FEED_RATE = 600.0
CONFIG_FILES = (
    'robot.json',
    'samples.json',
    'waste.json',
    'tips.json',
    'reagents.json',
    'eppendorf.json',
)
CODE_FILES = ('bernielib.py', 'samples.py', 'general.py')

# X offsets are cumulative positions relative to the tube centre, matching the
# existing low wall-wash path: +3, then 0, -0.629, -0.629 mm.
WALL_WASH_PATH = (
    (3.000, 24.0, 0.25),
    (3.000, 28.0, 0.50),
    (2.371, 32.0, 0.75),
    (1.742, 36.0, 1.00),
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


def makeSample(run_id, ber):
    """Create isolated state for the 30 uL tube at purification position 0."""
    state_path = os.path.join(EXPERIMENT_DIR, 'data',
                              'wall_wash_sample_' + run_id)
    state_name = os.path.relpath(state_path, REPO_ROOT)
    return bl.createSample('eppendorf', state_name, ber.samples_rack,
                           pos_col=TUBE_COLUMN, pos_row=TUBE_ROW,
                           volume=WASH_VOLUME_UL, purge=True)


def coordinatedWallWash(ber, sample, volume=WASH_VOLUME_UL,
                        feed_rate=DEFAULT_FEED_RATE):
    """Queue the four simultaneous XYZ/plunger segments and wait after the last."""
    x_center, y_center = sample.getCenterXY()
    z_top = sample.getSampleTopAbsZ(added_length=ber._calcExtraLength())
    last_index = len(WALL_WASH_PATH) - 1

    print('\n--- Coordinated wall wash: four queued G1 XYZ/A blocks ---')
    for index, (x_offset, z_from_top, fraction) in enumerate(WALL_WASH_PATH):
        dispense_volume = volume * fraction
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


def executeExperiment(ber, sample, feed_rate, state=None):
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

    print('\n--- Aspirating 30 uL from sample position 0 ---')
    ber.uptakeLiquid(sample, WASH_VOLUME_UL, lag_vol=5)
    coordinatedWallWash(ber, sample, WASH_VOLUME_UL, feed_rate)

    print('\n--- Dropping the tip into tip waste ---')
    ber.dumpTipToWaste()
    if state is not None:
        state['tip_may_be_attached'] = False

    print('\n--- Final home ---')
    ber.home()


def printDryPlan(feed_rate):
    print('DRY PLAN ONLY -- no robot object was created and no serial port was opened.')
    print('Would home; pickUpNextTip(); aspirate %.1f uL from samples [1,0];'
          % WASH_VOLUME_UL)
    print('queue four coordinated XYZ/A waypoints at F%s; dumpTipToWaste(); home.'
          % feed_rate)
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
        sample = makeSample(run_id, ber)

        executeExperiment(ber, sample, args.feed_rate, state=state)
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

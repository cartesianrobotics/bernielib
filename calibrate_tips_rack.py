"""
Calibrate the tips rack only, and store the measured centre.

This is the second half of calibrate.py, split out so the tips rack can be
measured on its own - it is the rack that gets swapped and re-seated, so it is
the one most often out of date.

Run calibrate_tube_racks.py first if the deck may have moved. That measures the
samples rack and re-seeds this rack's centre from it, which is what puts the
edge scan near the right place to begin with. This script does not calibrate the
tube racks itself: they are slow to measure and are not what is being corrected
here.

The measured centre is written to the real settings, so everything downstream
uses it. The previous values are backed up first, and every run leaves a report
in calibration_reports/ recording the edges found, the before and after values,
how many scans had to back off and retry, and any warnings.

Before running:
  - the tips rack in place, lid off (tips may or may not be present: the scans
    run outside the tip field and the Z probe lands on the rack frame)
  - no tubes anywhere in the working area
  - nothing on the pipette nozzle (the script ejects a tip anyway)

    python calibrate_tips_rack.py                    # show the plan, move nothing
    python calibrate_tips_rack.py --move-the-robot   # calibrate
    python calibrate_tips_rack.py --move-the-robot --revert    # trial run

Part of BernieLib.
"""

import sys

import bernielib as bl
from calibration_common import (parseArgs, requireRepoRootCwd, backupSettings,
                                restoreSettings, readSettings, run_record,
                                instrumented_scan, connectAndPrepare, finish)


RACK = 'tips'


def addArgs(parser):
    parser.add_argument('--tips-type', default='old', choices=['old', 'new'],
                        help="'old' is the Rainin-style green box; 'new' is the "
                             "Mettler Toledo rack in its adapter. Default: old.")


def main():
    args = parseArgs(__doc__, extra=addArgs)
    requireRepoRootCwd()

    rack_settings_name = RACK if args.tips_type == 'old' else 'new_tips'
    record = run_record('tips_rack', [rack_settings_name])
    record.before = readSettings([rack_settings_name])

    current = record.before.get(rack_settings_name, {})
    record.say("Calibrating the %s tips rack (settings file %s.json)."
               % (args.tips_type, rack_settings_name))
    record.say("")
    record.say("Current values:")
    record.say("  center (%s, %s), detected_z %s"
               % (current.get('center_x'), current.get('center_y'),
                  current.get('detected_z')))

    # Where the scan will start from, so a wrong stored centre is visible before
    # the robot moves rather than after.
    rack = bl.consumable(rack_settings_name)
    center_x, center_y = rack.getCenterXY()
    max_x, max_y, max_z = rack.getRackSize()
    record.say("  the X edge scans will start at %.3f and %.3f"
               % (center_x - max_x / 2.0, center_x + max_x / 2.0))
    record.say("  if those are not within a millimetre or two of the real rack edges,")
    record.say("  run calibrate_tube_racks.py first to re-seed this centre.")

    if not args.confirmed:
        record.say("")
        record.say("Nothing moved. Re-run with --move-the-robot to calibrate.")
        record.say("Check first: tips rack in place with the lid off, no tubes on the deck.")
        return 0

    backup = backupSettings([rack_settings_name], record.stamp)
    record.say("")
    record.say("Previous settings backed up to %s/" % backup)

    record.captureWarnings()
    ber = connectAndPrepare(record)
    try:
        record.say("")
        record.say("--- Calibrating the tips rack ---")
        with instrumented_scan(ber) as watch:
            x, y, z = ber.calibrateRack(rack=RACK)
        record.recordRack(rack_settings_name, x, y, z, watch.edges, watch.retries,
                          rack_size=ber._getRackObjectByName(rack_name=RACK).getRackSize())
        record.say("    center (%.3f, %.3f), Z %.3f" % (x, y, z))
        for axis, direction, coordinate in watch.edges:
            record.say("    edge %s direction %+d -> %s" % (axis, direction, coordinate))
        if watch.retries:
            record.say("    NOTE: %d scan(s) ran out of travel and backed off, meaning the"
                       % watch.retries)
            record.say("    stored centre was off by more than the scan could see from its")
            record.say("    starting point. The measured centre below is the corrected one.")
        else:
            record.say("    No scan needed to back off; the stored centre was close enough.")
    except bl.CalibrationScanError as e:
        record.aborted = str(e)
        record.say("")
        record.say("ABORTED: %s" % e)
        record.say("The tips rack centre is unchanged from before this run.")
    finally:
        finish(ber, record)
        record.releaseWarnings()

    record.after = readSettings([rack_settings_name])

    if args.revert:
        restored = restoreSettings([rack_settings_name], backup)
        record.reverted = True
        record.say("")
        record.say("--revert: restored %s from %s/" % (", ".join(restored), backup))
        record.after = readSettings([rack_settings_name])

    before, after = record.before.get(rack_settings_name, {}), record.after.get(rack_settings_name, {})
    record.say("")
    record.say("--- Result ---")
    record.say("  center (%s, %s) -> (%s, %s)"
               % (before.get('center_x'), before.get('center_y'),
                  after.get('center_x'), after.get('center_y')))
    record.say("  detected_z %s -> %s" % (before.get('detected_z'), after.get('detected_z')))
    if record.warnings:
        record.say("  %d warning(s) logged; see the report." % len(record.warnings))

    log_path, data_path = record.write()
    print("\nReport: %s" % log_path)
    print("Data:   %s" % data_path)
    return 1 if record.aborted else 0


if __name__ == '__main__':
    sys.exit(main())

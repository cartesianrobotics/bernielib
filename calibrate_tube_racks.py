"""
Calibrate the tube racks only - samples, reagents and the waste bin - and
re-seed the tips rack centre from the result.

This is the first half of calibrate.py, split out so the deck can be re-measured
without also redoing the tips rack. The samples rack is the reference for the
whole deck, so once it has been measured the tips rack centre is moved with it,
ready for calibrate_tips_rack.py to scan from a sensible starting point.

Results are written to the real settings files, so everything downstream uses
them. The previous values are backed up first, and every run leaves a report in
calibration_reports/ recording the coordinates found, the before and after
values, how many edge scans had to back off and retry, and any warnings.

Before running:
  - no tubes anywhere in the working area (the scans travel about 2 mm above
    the rack surface, so anything standing in a well is in the path)
  - the waste bin in place
  - nothing on the pipette nozzle (the script ejects a tip anyway, as a
    precaution)

    python calibrate_tube_racks.py                     # show the plan, move nothing
    python calibrate_tube_racks.py --move-the-robot    # calibrate
    python calibrate_tube_racks.py --move-the-robot --revert    # trial run

Part of BernieLib.
"""

import sys

import bernielib as bl
from calibration_common import (parseArgs, requireRepoRootCwd, backupSettings,
                                restoreSettings, readSettings, run_record,
                                instrumented_scan, connectAndPrepare, finish)


DEFAULT_RACKS = ['samples', 'reagents', 'waste']
SEEDED_RACK = 'tips'


def addArgs(parser):
    parser.add_argument('--racks', default=",".join(DEFAULT_RACKS),
                        help="Comma separated subset of %s. Default: all."
                             % ",".join(DEFAULT_RACKS))
    parser.add_argument('--no-seed-tips', action='store_true',
                        help="Skip moving the tips rack centre with the samples rack. "
                             "Worth using if the two racks turn out not to track each "
                             "other; see DEVLOG.md for 2026-08-07.")


def main():
    args = parseArgs(__doc__, extra=addArgs)
    requireRepoRootCwd()

    racks = [r.strip() for r in args.racks.split(',') if r.strip()]
    unknown = [r for r in racks if r not in DEFAULT_RACKS]
    if unknown:
        sys.exit("Unknown rack(s): %s. Choose from %s." % (unknown, DEFAULT_RACKS))

    reported = racks + ([SEEDED_RACK] if not args.no_seed_tips else [])
    record = run_record('tube_racks', reported)
    record.before = readSettings(reported)

    record.say("Calibrating tube racks: %s" % ", ".join(racks))
    if not args.no_seed_tips:
        if 'samples' in racks:
            record.say("The tips rack centre will be re-seeded from the samples rack.")
        else:
            record.say("Tips re-seeding needs the samples rack; it will be skipped.")
    record.say("")
    record.say("Current values:")
    for name in reported:
        values = record.before.get(name, {})
        record.say("  %-9s center (%s, %s), detected_z %s"
                   % (name, values.get('center_x'), values.get('center_y'),
                      values.get('detected_z')))

    if not args.confirmed:
        record.say("")
        record.say("Nothing moved. Re-run with --move-the-robot to calibrate.")
        record.say("Check first: no tubes in the working area, waste bin in place.")
        return 0

    backup = backupSettings(reported, record.stamp)
    record.say("")
    record.say("Previous settings backed up to %s/" % backup)

    record.captureWarnings()
    ber = connectAndPrepare(record)
    try:
        for name in racks:
            record.say("")
            record.say("--- Calibrating %s ---" % name)
            with instrumented_scan(ber) as watch:
                x, y, z = ber.calibrateRack(rack=name)
            record.recordRack(name, x, y, z, watch.edges, watch.retries)
            record.say("    center (%.3f, %.3f), Z %.3f" % (x, y, z))
            for axis, direction, coordinate in watch.edges:
                record.say("    edge %s direction %+d -> %s" % (axis, direction, coordinate))
            if watch.retries:
                record.say("    NOTE: %d scan(s) ran out of travel and backed off. "
                           "The stored centre was off; it is corrected now." % watch.retries)

            if name == 'samples' and not args.no_seed_tips:
                seeded = ber.seedRackCenterFromReference(SEEDED_RACK)
                if seeded is None:
                    record.say("    tips rack has no recorded offset; centre left alone.")
                else:
                    record.say("    tips rack centre re-seeded from samples: (%.3f, %.3f)"
                               % seeded)
                    record.say("    (an estimate, not a measurement - run "
                               "calibrate_tips_rack.py to measure it)")
    except bl.CalibrationScanError as e:
        record.aborted = str(e)
        record.say("")
        record.say("ABORTED: %s" % e)
        record.say("Racks calibrated before this point keep their new values.")
    finally:
        finish(ber, record)
        record.releaseWarnings()

    record.after = readSettings(reported)

    if args.revert:
        restored = restoreSettings(reported, backup)
        record.reverted = True
        record.say("")
        record.say("--revert: restored %s from %s/" % (", ".join(restored), backup))
        record.after = readSettings(reported)

    record.say("")
    record.say("--- Result ---")
    for name in reported:
        before = record.before.get(name, {})
        after = record.after.get(name, {})
        record.say("  %-9s center (%s, %s) -> (%s, %s), detected_z %s -> %s"
                   % (name, before.get('center_x'), before.get('center_y'),
                      after.get('center_x'), after.get('center_y'),
                      before.get('detected_z'), after.get('detected_z')))
    if record.warnings:
        record.say("  %d warning(s) logged; see the report." % len(record.warnings))

    log_path, data_path = record.write()
    print("\nReport: %s" % log_path)
    print("Data:   %s" % data_path)
    return 1 if record.aborted else 0


if __name__ == '__main__':
    sys.exit(main())

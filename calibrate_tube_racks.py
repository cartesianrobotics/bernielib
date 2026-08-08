"""
Calibrate the sample rack, and carry the result to the racks that share its body.

The samples and reagents "racks" are one physical part described twice: their
centre, size, calibration style, calibration Z and detected Z are all identical
in the settings, and only the well maps differ - two columns of twelve tubes for
samples, three by two large wells for reagents. Measuring both means feeling for
the same four edges twice, so this script measures once, as 'samples', and
copies the result to 'reagents'. Skipping reagents altogether would leave its
stored centre behind whenever the deck moved.

Once the samples rack is measured it also re-seeds the tips rack centre, ready
for calibrate_tips_rack.py to scan from a sensible starting point.

The waste bin is a separate part and is not measured unless --with-waste is
given. It is rarely disturbed, and the pipette only ever needs to be somewhere
above it.

Results are written to the real settings files, so everything downstream uses
them. The previous values are backed up first, and every run leaves a report in
calibration_reports/ recording the coordinates found, the before and after
values, how many edge scans had to back off and retry, and any warnings.

Before running:
  - no tubes anywhere in the working area (the scans travel about 2 mm above
    the rack surface, so anything standing in a well is in the path)
  - the waste bin in place (a tip is ejected into it before and after the run)
  - nothing on the pipette nozzle (the script ejects a tip anyway, as a
    precaution)

    python calibrate_tube_racks.py                     # show the plan, move nothing
    python calibrate_tube_racks.py --move-the-robot    # calibrate
    python calibrate_tube_racks.py --move-the-robot --with-waste
    python calibrate_tube_racks.py --move-the-robot --revert    # trial run

Part of BernieLib.
"""

import sys

import bernielib as bl
from calibration_common import (parseArgs, requireRepoRootCwd, backupSettings,
                                restoreSettings, readSettings, run_record,
                                instrumented_scan, connectAndPrepare, finish)


MEASURED_RACK = 'samples'
# Shares the same physical body as MEASURED_RACK; takes its result rather than
# being measured again.
MIRRORED_RACK = 'reagents'
SEEDED_RACK = 'tips'
OPTIONAL_RACK = 'waste'


def addArgs(parser):
    parser.add_argument('--with-waste', action='store_true',
                        help="Also calibrate the waste bin. Off by default: it is a "
                             "separate part, rarely moved, and only ever approached "
                             "from above.")
    parser.add_argument('--no-mirror-reagents', action='store_true',
                        help="Do not copy the samples result onto the reagents rack. "
                             "Only useful if the two stop sharing a body.")
    parser.add_argument('--no-seed-tips', action='store_true',
                        help="Skip moving the tips rack centre with the samples rack. "
                             "Worth using if the two racks turn out not to track each "
                             "other; see DEVLOG.md for 2026-08-07.")


def mirrorRackBody(ber, source_name, target_name, record):
    """
    Copies the measured geometry of one rack onto another that is physically the
    same part. Only the values calibration produces are copied; the well maps,
    which is all that really differs between them, are left alone.
    """
    source = ber._getRackObjectByName(rack_name=source_name)
    target = ber._getRackObjectByName(rack_name=target_name)
    x, y = source.getCenterXY()
    z = source.getZ()
    target.setCenterXY(x=x, y=y)
    target.setZ(z)
    record.say("    %s shares the %s body: centre (%.3f, %.3f) and Z %.3f copied across"
               % (target_name, source_name, x, y, z))


def main():
    args = parseArgs(__doc__, extra=addArgs)
    requireRepoRootCwd()

    measured = [MEASURED_RACK] + ([OPTIONAL_RACK] if args.with_waste else [])
    reported = list(measured)
    if not args.no_mirror_reagents:
        reported.append(MIRRORED_RACK)
    if not args.no_seed_tips:
        reported.append(SEEDED_RACK)

    record = run_record('tube_racks', reported)
    record.before = readSettings(reported)

    record.say("Measuring: %s" % ", ".join(measured))
    if not args.no_mirror_reagents:
        record.say("Copying the %s result to %s (same physical rack)."
                   % (MEASURED_RACK, MIRRORED_RACK))
    if not args.no_seed_tips:
        record.say("Re-seeding the %s rack centre from %s." % (SEEDED_RACK, MEASURED_RACK))
    if not args.with_waste:
        record.say("Not touching the waste bin (pass --with-waste to include it).")
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
        for name in measured:
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

            if name == MEASURED_RACK:
                if not args.no_mirror_reagents:
                    mirrorRackBody(ber, MEASURED_RACK, MIRRORED_RACK, record)
                if not args.no_seed_tips:
                    seeded = ber.seedRackCenterFromReference(SEEDED_RACK)
                    if seeded is None:
                        record.say("    tips rack has no recorded offset; centre left alone.")
                    else:
                        record.say("    tips rack centre re-seeded: (%.3f, %.3f)" % seeded)
                        record.say("    (an estimate, not a measurement - run "
                                   "calibrate_tips_rack.py to measure it)")
    except bl.CalibrationScanError as e:
        record.aborted = str(e)
        record.say("")
        record.say("ABORTED: %s" % e)
        record.say("Anything calibrated before this point keeps its new values.")
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

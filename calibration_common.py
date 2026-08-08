"""
Shared pieces for the single-purpose calibration scripts.

calibrate.py does the whole deck in one interactive run. These scripts split it
so that one rack group can be redone without repeating the rest, and so that
every run leaves a record: the coordinates found, the values before and after,
whether the bounded edge scan had to back off and retry, and any warnings.

Every run backs the affected settings up first. The live calibration files are
excluded by /*.json in .gitignore, so they are not in version control and a bad
run would otherwise overwrite them with nothing to restore from - which is what
happened to tips.json on 2026-08-07.

Part of BernieLib.
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import sys

import bernielib as bl


REPORT_DIR = 'calibration_reports'
BACKUP_DIR_PREFIX = 'calibration_backup_'

# Settings worth recording before and after, per rack.
TRACKED_SETTINGS = ['center_x', 'center_y', 'detected_z']

# Every edge a scan reports sits about one pipette-end radius outside the real
# rack edge: the nozzle keeps pressing on the rack until its centre has passed
# the edge by its own radius, and only then does the probe drop. Both edges of an
# axis are pushed outward by the same amount, so
#
#     X_measured = X_CAD + D_pipette
#     Y_measured = Y_CAD + D_pipette
#
# The centre is unaffected - the two biases cancel - which is why the centre is
# the trustworthy output of a calibration and the span between the edges is not.
#
# The pipette end is a Rainin LTS for 200 ul tips (p200). It is circular, so the
# bias is the same on X and Y, and conical: 5.9 mm across at the very end,
# widening to 6.2 mm ten millimetres up. The 5.9 mm figure is the one that
# matters here, since it is the end that rides the rack surface.
#
# Where max_x / max_y are the true body dimensions, measured span minus max_x
# reads out the effective diameter. Measured 5.4 mm in X and 5.2 mm in Y against
# the samples rack body on 2026-08-08 - a little under the geometric 5.9, the
# load threshold evidently releasing shortly before the rim fully clears the
# edge.
#
# The figure that comes back is not the same for every rack, because it depends
# on the edge profile and on how far there is to fall beyond it. Measured on
# 2026-08-08, with both bodies confirmed against CAD:
#
#     samples body, 158 x 180 mm      X 5.4    Y 5.2
#     tips box,     86.8 x 123.7 mm   X 4.45   Y 3.6
#
# The tips box reads lower on both axes and lower again on Y. Its rim is not the
# clean vertical step the samples plate has, and beyond it the nozzle lands on
# the samples frame only about 4.7 mm below rather than dropping away entirely,
# so the scan calls the edge at a smaller lateral offset. The box is also thin
# flexible plastic, which may give under the probing load and let the nozzle
# start down sooner than a rigid edge would - plausible, but not established.
# None of this affects the centre, which is what calibration stores.
#
# So compare a run against earlier runs of the SAME rack, not against 5.9. The
# range below is only a coarse net for a scan that has gone badly wrong.
#
# An implausible figure has two possible causes, worth telling apart: either the
# scan found something other than the two rack edges, in which case the centre is
# wrong too, or the rack's stored max_x / max_y is not its real body dimension,
# in which case the centre is fine and only this check is misled.
PIPETTE_END_DIAMETER = 5.9
PIPETTE_END_DIAMETER_10MM_UP = 6.2
PIPETTE_END_DIAMETER_PLAUSIBLE = (3.0, 9.0)


def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def parseArgs(description, extra=None):
    """
    Nothing moves without --move-the-robot. Without it the script prints what it
    would calibrate and what the current values are, then exits.
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--move-the-robot', action='store_true', dest='confirmed',
                        help="Required to actually calibrate. Stand at the robot.")
    parser.add_argument('--revert', action='store_true',
                        help="Restore the pre-run settings afterwards. Use for a trial "
                             "run; without it the results are kept and everything "
                             "downstream will use them.")
    if extra is not None:
        extra(parser)
    return parser.parse_args()


def requireRepoRootCwd():
    """Settings are read relative to the working directory."""
    if not os.path.isfile('robot.json') or not os.path.isfile('bernielib.py'):
        sys.exit("Run this from the repository root - settings files are read "
                 "relative to the working directory.")


def backupSettings(rack_names, stamp):
    """
    Copies the settings files this run may overwrite. Returns the directory.
    """
    directory = BACKUP_DIR_PREFIX + stamp
    os.makedirs(directory, exist_ok=True)
    for name in list(rack_names) + ['robot']:
        source = name + '.json'
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(directory, source))
    return directory


def restoreSettings(rack_names, directory):
    """Puts the pre-run settings back, for --revert."""
    restored = []
    for name in rack_names:
        source = os.path.join(directory, name + '.json')
        if os.path.isfile(source):
            shutil.copy2(source, name + '.json')
            restored.append(name + '.json')
    return restored


def readSettings(rack_names):
    """Current tracked values for each rack, straight from the JSON on disk."""
    snapshot = {}
    for name in rack_names:
        try:
            with open(name + '.json') as f:
                data = json.load(f)
        except (IOError, ValueError):
            continue
        snapshot[name] = {k: data.get(k) for k in TRACKED_SETTINGS}
    return snapshot


def describeSpans(edges, rack_size):
    """
    Turns the edge coordinates a calibration found into a per-axis sanity check.

    Returns {axis: {'low', 'high', 'span', 'body', 'implied_pipette_diameter',
    'plausible'}}. rack_size is (max_x, max_y, max_z) as stored for the rack, the
    true body dimensions; None skips the comparison.
    """
    body_for_axis = {}
    if rack_size is not None:
        body_for_axis = {'X': rack_size[0], 'Y': rack_size[1]}

    by_axis = {}
    for axis, direction, coordinate in edges:
        if coordinate is None:
            continue
        by_axis.setdefault(axis.upper(), []).append(coordinate)

    spans = {}
    for axis, coordinates in by_axis.items():
        if len(coordinates) < 2:
            continue
        low, high = min(coordinates), max(coordinates)
        entry = {'low': low, 'high': high, 'span': high - low,
                 'body': body_for_axis.get(axis),
                 'implied_pipette_diameter': None, 'plausible': None}
        if entry['body']:
            implied = entry['span'] - entry['body']
            entry['implied_pipette_diameter'] = implied
            entry['plausible'] = (PIPETTE_END_DIAMETER_PLAUSIBLE[0] <= implied
                                  <= PIPETTE_END_DIAMETER_PLAUSIBLE[1])
        spans[axis] = entry
    return spans


def formatSpans(spans, indent="      "):
    """Report lines for what describeSpans() worked out."""
    lines = []
    for axis in sorted(spans):
        entry = spans[axis]
        if entry['implied_pipette_diameter'] is None:
            lines.append("%s%s span %.3f (%.3f .. %.3f)"
                         % (indent, axis, entry['span'], entry['low'], entry['high']))
            continue
        verdict = ("ok" if entry['plausible'] else
                   "SUSPECT - either the scan missed the rack edges, or this rack's "
                   "stored body size is wrong")
        lines.append("%s%s span %.3f vs body %.1f -> pipette end diameter %.3f mm  [%s]"
                     % (indent, axis, entry['span'], entry['body'],
                        entry['implied_pipette_diameter'], verdict))
    return lines


class run_record:
    """
    Collects everything observed during a calibration run, prints it as it goes,
    and writes it out as a readable report plus a machine-readable copy.
    """

    def __init__(self, title, rack_names):
        self.title = title
        self.rack_names = list(rack_names)
        self.stamp = timestamp()
        self.lines = []
        self.racks = {}
        self.before = {}
        self.after = {}
        self.warnings = []
        self.aborted = None
        self.reverted = False
        os.makedirs(REPORT_DIR, exist_ok=True)
        self.log_path = os.path.join(REPORT_DIR, '%s_%s.txt' % (self.stamp, title))
        self.data_path = os.path.join(REPORT_DIR, '%s_%s.json' % (self.stamp, title))

    def say(self, message=''):
        """Print and record, so the report holds what the operator saw."""
        print(message)
        self.lines.append(message)

    def recordRack(self, rack_name, x, y, z, edges, retries, rack_size=None):
        self.racks[rack_name] = {
            'center_x': x, 'center_y': y, 'detected_z': z,
            'edges': edges, 'scan_retries': retries,
            'spans': describeSpans(edges, rack_size),
        }

    def captureWarnings(self):
        """
        Routes bernielib's warnings into the report. A backed-off edge scan logs
        a warning rather than failing, so without this the report would not show
        that a scan had trouble.
        """
        record = self.warnings

        class handler(logging.Handler):
            def emit(self, entry):
                if entry.levelno >= logging.WARNING:
                    record.append("%s: %s" % (entry.levelname, entry.getMessage()))

        self._handler = handler()
        self._handler.setLevel(logging.WARNING)
        logging.getLogger().addHandler(self._handler)
        # bernielib logs at INFO; make sure the root logger passes warnings on.
        if logging.getLogger().level > logging.WARNING:
            logging.getLogger().setLevel(logging.WARNING)

    def releaseWarnings(self):
        handler = getattr(self, '_handler', None)
        if handler is not None:
            logging.getLogger().removeHandler(handler)

    def write(self):
        report = []
        report.append("Calibration run: %s" % self.title)
        report.append("Time: %s" % self.stamp)
        report.append("Racks: %s" % ", ".join(self.rack_names))
        report.append("Results kept: %s" % ("no - reverted" if self.reverted else "yes"))
        if self.aborted:
            report.append("ABORTED: %s" % self.aborted)
        report.append("")
        report.append("--- Values before and after ---")
        for name in self.rack_names:
            before = self.before.get(name, {})
            after = self.after.get(name, {})
            report.append("  %s:" % name)
            for key in TRACKED_SETTINGS:
                b, a = before.get(key), after.get(key)
                delta = ''
                if isinstance(b, (int, float)) and isinstance(a, (int, float)):
                    delta = '   (%+.3f)' % (a - b)
                report.append("    %-12s %-10s -> %-10s%s" % (key, b, a, delta))
        report.append("")
        report.append("--- What each scan found ---")
        for name, found in self.racks.items():
            report.append("  %s: center (%.3f, %.3f), Z %.3f, scan retries %d"
                          % (name, found['center_x'], found['center_y'],
                             found['detected_z'], found['scan_retries']))
            for axis, direction, coordinate in found['edges']:
                report.append("      edge %s direction %+d -> %s" % (axis, direction, coordinate))
            report.extend(formatSpans(found.get('spans', {})))
        report.append("")
        report.append("--- Warnings and errors ---")
        if self.warnings:
            report.extend("  " + w for w in self.warnings)
        else:
            report.append("  (none)")
        report.append("")
        report.append("--- Session output ---")
        report.extend("  " + line for line in self.lines)

        with open(self.log_path, 'w') as f:
            f.write("\n".join(report) + "\n")
        with open(self.data_path, 'w') as f:
            json.dump({
                'title': self.title, 'timestamp': self.stamp,
                'racks': self.rack_names, 'results_kept': not self.reverted,
                'aborted': self.aborted, 'before': self.before, 'after': self.after,
                'found': self.racks, 'warnings': self.warnings,
            }, f, indent=2)
        return self.log_path, self.data_path


class instrumented_scan:
    """
    Watches the edge scans for one rack: every edge coordinate returned, and how
    many scans ran out of travel and had to back off. Both are the interesting
    part of a calibration run and neither is visible in the stored settings.
    """

    def __init__(self, ber):
        self.ber = ber
        self.edges = []
        self.retries = 0

    def __enter__(self):
        self._scanForStairFine = self.ber.scanForStairFine
        self._scanForStair = self.ber.scanForStair

        def watchedFine(axis, direction):
            found = self._scanForStairFine(axis, direction)
            self.edges.append((axis, direction, found))
            return found

        def watchedCoarse(*a, **kw):
            found = self._scanForStair(*a, **kw)
            if found is None:
                self.retries += 1
            return found

        self.ber.scanForStairFine = watchedFine
        self.ber.scanForStair = watchedCoarse
        return self

    def __exit__(self, *exc):
        self.ber.scanForStairFine = self._scanForStairFine
        self.ber.scanForStair = self._scanForStair
        return False


def connectAndPrepare(record):
    """
    Connects, homes, and ejects anything on the nozzle.

    The tip ejection is not just tidiness: calibration stores bare-nozzle
    heights and bernielib cannot tell whether a tip is attached, so a tip left
    from an earlier run would put every recorded Z out by its length (41.6 mm).
    tip_attached is forced to 1 first so the travel height allows for one.
    """
    record.say("Connecting (bernielib scans the serial ports; this takes a moment)...")
    ber = bl.robot()
    record.say("  cartesian: %s" % ber.cartesian_port.port)
    record.say("  loadcell:  %s" % ber.loadcell_port.port)
    record.say("")
    record.say("Homing, then ejecting any tip (a tip would corrupt every height)...")
    ber.home()
    ber.tip_attached = 1
    ber.dumpTipToWaste()
    return ber


def finish(ber, record):
    """Eject anything picked up during the run, home, and power down."""
    record.say("")
    record.say("Finishing: ejecting any tip, then homing...")
    try:
        ber.tip_attached = 1
        ber.dumpTipToWaste()
        ber.home()
        ber.powerStepperOff()
    finally:
        ber.close()
        record.say("Ports closed.")

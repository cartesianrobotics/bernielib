"""
Shared scaffolding for the physical tests.

These tests drive the real robot. They are deliberately kept out of the normal
suite: they live outside tests/ and are named physical_test_*.py, so neither
`python -m unittest discover tests` nor a discover run with the default
'test*.py' pattern can pick them up by accident. Nothing here runs unless a
person asks for it by name and passes --move-the-robot.

Every physical test is wrapped in physical_test(), which homes the robot and
ejects anything on the nozzle before the test body, and again afterwards -
including when the body fails or raises. A tip left on the nozzle is the
failure mode worth guarding against: bernielib tracks tip_attached in memory
only, so a fresh robot object believes the nozzle is bare, and every Z it
computes is then wrong by the tip length (41.6 mm in robot.json).

Part of BernieLib.
"""

import argparse
import os
import sys

# Allow `python physical_tests/physical_test_*.py` from the repository root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import bernielib as bl


CONFIRM_FLAG = '--move-the-robot'


def parseArgs(description, extra=None):
    """
    Every physical test needs --move-the-robot before it will move anything.
    Without it the test prints what it would do and exits, so that running the
    file out of curiosity cannot start the machine.

    `extra` is an optional callback taking the parser, for tests with their own
    arguments.
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(CONFIRM_FLAG, action='store_true', dest='confirmed',
                        help="Required to actually move. Stand at the robot before using it.")
    if extra is not None:
        extra(parser)
    return parser.parse_args()


def requireRepoRootCwd():
    """
    Settings are loaded relative to the working directory (rack('tips') reads
    ./tips.json), so a test run from anywhere else would silently read the
    wrong calibration, or none.
    """
    if not os.path.isfile('robot.json') or not os.path.isfile('bernielib.py'):
        sys.exit("Run this from the repository root - settings files are read "
                 "relative to the working directory.\n"
                 "    cd %s" % REPO_ROOT)


class physical_test:
    """
    Context manager that makes the robot safe before and after a physical test.

    Before the body: home, then eject any tip.
    After the body:  eject any tip, then home.

    The tip ejection is precautionary - usually there is no tip. It assumes the
    worst on purpose; see _ejectAnyTip().
    """

    def __init__(self, name):
        self.name = name
        self.ber = None

    def __enter__(self):
        print("Connecting (bernielib scans the serial ports; this takes a moment)...")
        self.ber = bl.robot()
        print("  cartesian: %s" % self.ber.cartesian_port.port)
        print("  loadcell:  %s" % self.ber.loadcell_port.port)
        print("\n--- Preparing: homing, then ejecting any tip ---")
        self.ber.home()
        self._ejectAnyTip()
        return self.ber

    def __exit__(self, exc_type, exc_value, traceback):
        if self.ber is not None:
            try:
                print("\n--- Finishing: ejecting any tip, then homing ---")
                self._ejectAnyTip()
                self.ber.home()
                self.ber.powerStepperOff()
            finally:
                self.ber.close()
                print("Ports closed.")
        return False    # never swallow an exception from the test body

    def _ejectAnyTip(self):
        """
        Drops a tip into the waste bin, whether or not one is believed to be
        attached.

        tip_attached is forced to 1 first. moveToWell() works out its safe
        travel height from the tip length times that flag, so leaving it at 0
        while a tip really is attached would take the robot to a height that is
        safe for a bare nozzle and 41.6 mm too low for a tipped one. Claiming a
        tip that is not there only costs a little extra clearance; the reverse
        costs a collision. dumpTip() resets the flag to 0 afterwards.
        """
        self.ber.tip_attached = 1
        self.ber.dumpTipToWaste()


class checklist:
    """Collects pass/fail checks so a physical test reports like a test."""

    def __init__(self):
        self.results = []

    def check(self, description, passed, detail=''):
        self.results.append((description, bool(passed)))
        print("  [%s] %s%s" % ("PASS" if passed else "FAIL", description,
                               ("  -- " + detail) if detail else ''))
        return passed

    def report(self):
        failed = [d for d, ok in self.results if not ok]
        print("\n--- %d checks, %d failed ---" % (len(self.results), len(failed)))
        for description in failed:
            print("  FAILED: %s" % description)
        return 1 if failed else 0

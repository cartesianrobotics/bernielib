"""Test package for bernielib.

Importing purify has a side effect: at import time it calls logging.basicConfig
with a filename of <timestamp>purify.log, so every single test run drops another
log file into the working directory. Those accumulate forever.

The obvious fix would be to move that basicConfig call in purify.py behind an
"if __name__ == '__main__'" guard, so that importing the module stops writing
files. That was looked at and deliberately rejected, because it would quietly
change how real runs are recorded:

  - purify.py is not only run as a script. Six notebooks, among them
    21121701_Bernie_Test.ipynb and jupyter_notebooks/21112901_Bernie_Test.ipynb,
    start with "import purify" and then drive an actual purification.
  - logging.basicConfig does nothing when the root logger already has handlers.
    Those notebooks call basicConfig themselves, but purify has already
    configured the root logger by the time the notebook gets to it, so the
    notebook call is a no-op and purify's settings are the ones in force:
    DEBUG level, plus the console handler that purify adds.
  - Guarding purify's call would leave the root logger unconfigured at that
    point, so the notebook's own call would start taking effect instead. Real
    runs would silently move to a different file at INFO instead of DEBUG and
    lose the console handler.

Changing that is a decision about how the robot records its runs, not a test
concern, so purify.py is left exactly as it is and the cleanup happens here
instead. Only the handler this process opened is touched, so a log written by an
actual robot run is never at risk.

This only takes effect when the test files are imported as the "tests" package,
that is with "python -m unittest discover -s tests -t ." or "python -m unittest
tests.test_samples". Plain "python -m unittest discover tests" imports them as
top level modules and never runs this file. See readme_tests.txt.
"""

import atexit
import logging
import os


def _remove_log_file_created_by_importing_purify():
    for handler in list(logging.root.handlers):
        filename = getattr(handler, 'baseFilename', None)
        if filename is None or not filename.endswith('purify.log'):
            continue
        logging.root.removeHandler(handler)
        handler.close()
        try:
            os.remove(filename)
        except OSError:
            # Never fail a run over a leftover log file.
            pass


atexit.register(_remove_log_file_created_by_importing_purify)

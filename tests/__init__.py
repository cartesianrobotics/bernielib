"""Test package for bernielib.

Importing purify has a side effect: at import time it calls logging.basicConfig
with a filename of <timestamp>purify.log, so every single test run drops another
log file into the working directory. Those accumulate forever.

The real fix belongs in purify.py, which should not configure logging just
because it was imported. That is robot code rather than test code, so it is left
alone here. Instead the file the current process created is removed once the run
is over. Only the handler this process opened is touched, so logs written by an
actual robot run are never at risk.

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

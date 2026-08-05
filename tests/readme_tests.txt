Setup (first time only), from the repository root:
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

To run all the tests, open a command line at the repository root and type:
python -m unittest discover -s tests -t .

here "tests" is the directory where test files are stored, and "-t ." says the
repository root is the top of the package tree.
Run from the repository root, otherwise the imports and the settings files the
tests write will not resolve.

Plain "python -m unittest discover tests" also runs everything and passes, but
it imports the test files as top level modules instead of as the "tests"
package, which means tests/__init__.py never runs. That file cleans up the log
file purify.py creates when it is imported, so with the shorter command every
run leaves another <timestamp>purify.log behind in the repository root.

To run only a specific test file, run:
python -m unittest tests.test_samples

To run a single test case:
python -m unittest tests.test_samples.bernielib_test_case.test_isLowVolumeUptakeNeeded

Note: these tests mock the serial ports, so the robot does NOT need to be
connected. The one exception is real_robot_test__purify_one_cutoff.py in the
repository root -- that one drives the actual hardware and prompts for input,
so it is deliberately named so that "discover" does not pick it up.

To run all the tests, open a command line and type:
python -m unittest discover tests

here "tests" is the directory where test files are stored.

To run only a specific test file, run:
python -m unittest discover -s tests -p '*_test.py'
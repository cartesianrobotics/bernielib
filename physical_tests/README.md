# Physical tests

Tests that drive the real robot. **These move the machine.** Stand at it, and
keep a hand near the power switch.

They are not part of the normal suite and never run by accident:

- they live outside `tests/`, so `python -m unittest discover tests` cannot see them;
- they are named `physical_test_*.py`, which does not match unittest's default
  `test*.py` pattern, so even a repo-wide discover skips them (verified);
- each one refuses to move unless given `--move-the-robot`.

Without that flag a test prints the coordinates it would visit and exits, which
is the sensible way to check that a test is aimed where you think it is.

## Running one

From the repository root — settings are read relative to the working directory,
so running from anywhere else reads the wrong calibration or none:

```
.venv\Scripts\python.exe physical_tests\physical_test_edge_search.py
.venv\Scripts\python.exe physical_tests\physical_test_edge_search.py --move-the-robot
```

Exit status is 0 when every check passed.

## What every physical test does for you

`harness.physical_test` wraps each test so that it:

1. homes, then ejects any tip, before the body runs;
2. ejects any tip, then homes, afterwards — including when the body fails.

The tip ejection is precautionary. `bernielib` tracks `tip_attached` in memory
only, so a freshly constructed robot believes the nozzle is bare; if a tip was
left on it from an earlier run, every Z the library computes is wrong by the tip
length (41.6 mm). The harness therefore assumes a tip **is** attached when
working out its safe travel height. Claiming a tip that is not there costs a
little extra clearance; assuming a bare nozzle when one is attached costs a
collision.

## The tests

| File | What it checks | Prerequisite |
|---|---|---|
| `physical_test_edge_search.py` | The edge scan stops after 8 mm rather than walking across the deck, backs off 4 mm past its start, and finds the real edge on the retry. Reproduces the 2026-08-07 calibration runaway. | **Calibrate the tips rack first** — the test derives the true edge from the stored centre and starts a known 2 mm outside it. A stale centre means it starts somewhere else entirely and the test measures nothing. |

## Experiments

These live here too, named `physical_experiment_*.py`. They answer a question
rather than assert a pass or fail, but they move the robot, so they use the same
harness and the same `--move-the-robot` gate.

| File | Question |
|---|---|
| `physical_experiment_side_load.py` | Do the load cells register a sideways approach at all? |
| `physical_experiment_side_edge_find.py` | Can a rack edge be found sideways, and does it agree with Z-tapping? |

Findings, the datasets, and — importantly — **the conclusions that turned out to
be wrong and why** are written up in
[`../experiment_reports/README.md`](../experiment_reports/README.md). Read that
before relying on any number these produce.

Each test deliberately leaves calibration alone: a full rack calibration is slow
and is not what these are testing.

## Adding one

Use the harness, take the confirmation flag, and describe the plan before
moving:

```python
from harness import parseArgs, requireRepoRootCwd, physical_test, checklist

args = parseArgs(__doc__)
requireRepoRootCwd()
# ... print the coordinates the test will visit ...
if not args.confirmed:
    return 0

results = checklist()
with physical_test('what this checks') as ber:
    ...
    results.check("description", condition, "detail")
return results.report()
```

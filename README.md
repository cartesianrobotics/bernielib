# bernielib
 Library for Bernie robot, automatic DNA purifier

## Setup

The project runs from a virtual environment at the repo root. Create it once:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Then activate it in each new shell:

```bash
.venv\Scripts\Activate.ps1
```

`.venv/` is gitignored, so a fresh clone needs the step above. Use this
environment for everything — the dependencies (pyserial, pandas, scipy) are not
installed system-wide, so `import bernielib` fails outside it.

## Tests

No hardware required:

```bash
.venv/Scripts/python.exe -m unittest discover tests
```

## Checking the robot

With the robot plugged in and powered, `hello_robot.py` asks both controllers
(the Smoothieboard and the load cell Arduino) to identify themselves and report
status. It sends only read-only commands — nothing moves:

```bash
.venv/Scripts/python.exe hello_robot.py
```

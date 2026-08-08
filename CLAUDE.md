# Bernie / bernielib

Library for the Bernie robot, an automatic DNA purifier.

## Python environment — always use `.venv`

This project runs from a virtual environment at the repo root. **Use it for
everything**: running scripts, running tests, checking an import, driving the
robot. Do not use the system Python or a conda env — none of them have the
dependencies, so `import bernielib` fails there with `ModuleNotFoundError`.

```bash
.venv/Scripts/python.exe hello_robot.py
```

To activate it in a PowerShell session instead of prefixing every command:

```bash
.venv\Scripts\Activate.ps1
```

If `.venv/` is missing (it is gitignored, so a fresh clone has none), recreate it:

```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt
```

Dependencies live in [requirements.txt](requirements.txt); add new ones there.
Verified against Python 3.13 on Windows.

## Tests

78 tests, no hardware needed:

```bash
.venv/Scripts/python.exe -m unittest discover tests
```

## Hardware

Two serial boards, both at 115200 baud, auto-detected by sending `version` to
every port and matching the reply (`robot._mapPorts()` in `bernielib.py`):

| Board | Identifies as | Line terminator |
|---|---|---|
| Smoothieboard (motion, G-code) | `Build version: ...` | `\r` |
| Load cell Arduino (`firmware_arduino/bernie.ino`) | `Bernie's load cells controller` | none |

The Arduino needs no terminator because it reads with `Serial.readBytes()` on a
20 ms timeout. Getting this wrong is a silent hang, not an error.

`hello_robot.py` is a read-only check that both boards are alive and answering
(and that bernielib's reply parsers still match the firmware). It touches
nothing that moves, so it is the safe first thing to run on a robot that has
just been plugged in.

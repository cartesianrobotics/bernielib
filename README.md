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

## Calibration

`calibrate.py` measures the whole deck interactively. To redo one part without
repeating the rest:

```bash
.venv/Scripts/python.exe calibrate_tube_racks.py --move-the-robot
.venv/Scripts/python.exe calibrate_tips_rack.py --move-the-robot
```

Neither moves without `--move-the-robot`; without it they print the plan and the
current values. Each backs up the settings first and writes a report to
`calibration_reports/`.

### Measured edges read wide, and by how much

A rack is measured by pressing the nozzle down and stepping sideways until it
falls off the edge. The nozzle keeps contact until its *centre* has passed the
edge by roughly its own radius, so every edge is reported about one radius
outside the real one, and the span between two edges is a whole diameter too
large:

```
X_measured = X_CAD + D_pipette
Y_measured = Y_CAD + D_pipette
```

Both edges of an axis are biased outward equally, so **the centre is unaffected**
— which is why the centre is what calibration stores and trusts, and why the
span between the edges is not a measurement of the rack.

`D_pipette` is a property of the nozzle, not the rack. The end is a **Rainin LTS
for 200 µL tips (p200)**: circular, so the bias is identical on X and Y, and
conical — **5.9 mm** across at the very end, widening to 6.2 mm ten millimetres
up. The 5.9 mm figure is the one that applies, since it is the end that rides the
rack surface.

Where `max_x` / `max_y` are true body dimensions, measured span minus `max_x`
reads the effective diameter back out. Against the samples rack body — 158 × 180
mm, confirmed against CAD — it measured 5.4 mm in X and 5.2 mm in Y, a little
under the geometric 5.9 because the load threshold releases shortly before the
rim fully clears the edge.

The reports print this per axis and flag anything outside 3–9 mm. A flag has two
possible causes, worth telling apart:

- the scan found something other than the two rack edges, so the centre is wrong
  too — the 2026-08-07 runaway would have reported 2.3 mm;
- the rack's stored `max_x` / `max_y` is not its real body size, so the centre is
  fine and only this check is misled. Only the samples body is CAD-confirmed; the
  tips rack reads 4.0 mm in X and 2.8 mm in Y, which suggests its stored 87.25 ×
  124.5 is about 2–3 mm too large rather than that its calibration is bad.

## Checking the robot

With the robot plugged in and powered, `hello_robot.py` asks both controllers
(the Smoothieboard and the load cell Arduino) to identify themselves and report
status. It sends only read-only commands — nothing moves:

```bash
.venv/Scripts/python.exe hello_robot.py
```

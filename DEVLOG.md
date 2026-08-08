# Bernie dev log

Running record of work on the robot and the library. Newest entry first.
Ongoing tasks live in [general_todo.txt](general_todo.txt); this file is what
happened and when.

---

## 2026-08-08, 01:45–04:00 CDT — can the load cells find an edge sideways?

Calibration finds an edge by tapping downwards, and every lateral step costs a
full descend-until-press cycle. That is where calibration spends its time. A
sideways touch would need one approach instead, so the question was whether the
cells register horizontal contact at all, and whether the edge they report
matches the tapping method.

They do — one increment 93× the previous. Two things had to be dealt with first.

**The cells drift with carriage position while touching nothing.** Both ramp
steadily as soon as the carriage moves, the right about 2.7× as far as the left
and opposite in sign. Confirmed by a control run 20 mm above the rack, where
contact is impossible, and by eye at the machine with 2–3 mm still to go. It is
the mount reacting to the carriage's own geometry. Every side is therefore
measured twice: once above the rack for a background, once at working height
with that background subtracted, which holds the corrected signal inside ±1.6
until contact.

**Two detection rules were wrong before this settled.** Contact is a step
change, not exponential growth, so a rule wanting four consecutive doublings
never fires. And contact magnitude ranges from 4.4 to 91 across four edges, so
no fixed cutoff works — 70 caught one edge in four and let another run 3 mm into
the rack unnoticed. Detection now scales to the flat band each run measures for
itself.

All four edges of the samples rack agree with Z-tapping within 0.3 mm, repeating
to 0.06 mm within a run.

**The left X edge did not, for several hours.** It read 1.100 mm high three times
running and looked like a real feature on that wall. It was the carriage fouling
the far end of X travel at the start of the approach, losing about 0.8 mm of
steps that every later position inherited. Backing the start off 1.5 mm gives
168.900; a further 1.0 mm changes it by 0.067, so it has converged.
`USABLE_MAX['X'] = 171.4` now caps the start, making the good configuration the
default.

Conclusions withdrawn once the cause was found: that something is physically
proud by ~1.1 mm on the left wall, and that the X span and centre disagree with
Z-tapping by 1.200 and 0.500 mm. All the same artifact. The wall-draft
ruling-out survives, resting only on the Y measurements.

Written up with the eleven datasets in
[experiment_reports/README.md](experiment_reports/README.md), including which
file holds the contaminated run. Not a calibration method yet: how far one
background generalises, where a residual ~0.2 mm offset comes from, and whether
other racks behave the same are all open.

### Also found

- **`robot.json` claims `x_max: 189`, which is not reachable.** The carriage
  fouls the end of travel well before it. Left as-is in case other code depends
  on it, but it is wrong.
- Travel path does not affect the reading: repeating all four edges with the
  full-height lifts replaced by a safe-height traverse reproduced both X edges
  bit-identically.

## 2026-08-08, 00:00–01:30 CDT — calibration split per rack, pipette geometry recorded

`calibrate.py` does the whole deck in one interactive run, so re-measuring one
rack meant repeating the rest. Split into `calibrate_tube_racks.py` and
`calibrate_tips_rack.py`. Both write to the real settings, back up first, refuse
to move without `--move-the-robot`, and leave a report in
`calibration_reports/` recording the edges found, before and after values, and
how many scans had to back off — that last number says whether the stored centre
was near enough to scan from, which is invisible in the settings themselves.

**The samples and reagents racks are one physical part described twice.** Every
value calibration writes was already identical between them; only the well maps
differ. So the body is measured once as `samples` and the result copied to
`reagents`. Dropping reagents entirely would have been wrong — its centre would
then lag whenever the deck moved. The waste bin is no longer measured by
default.

**Pipette end geometry, from the CAD model:** Rainin LTS for 200 µL tips,
circular, 5.9 mm at the end and 6.2 mm ten millimetres up. Every edge a scan
reports sits about one radius outside the real one, so `X_measured = X_CAD +
D_pipette`; the centre is unaffected because both edges shift equally. The
reports now invert this per axis as a sanity check. It does not read the same on
every rack — 5.4/5.2 mm on the samples body against 4.45/3.6 mm on the tips box —
so compare a run against earlier runs of the same rack, not against 5.9. The
tips box may read short because it is thin flexible plastic that gives under the
probe; plausible, not established.

Tips box corrected to its CAD dimensions, 86.8 × 123.7 mm.

**Repeatability of the tapping method looks like ±1 mm.** Three measurements of
the samples centre gave 86.0, 88.0 and 86.9. An earlier claim that the deck had
shifted +2.000 mm was weaker than presented: samples and reagents are the same
measurement written twice, so it was two data points, not three.

## 2026-08-07, 21:15–23:00 CDT — calibration runaway, diagnosed and bounded

The first full `calibrate.py` run drove the pipette 16 mm onto the neighbouring
rack and picked up a tip. Two independent faults.

`scanForStair()` had **no limit on lateral travel**. Its loop ended only when a
downward probe found a drop, so a scan beginning off the rack — on flat deck —
stepped sideways indefinitely. The deck had moved ~2 mm in X since the tips rack
was last calibrated, putting the scan start just past the true edge. It ran until
it fell off the samples rack instead, and the centre came out 7.1 mm wrong. That
moved the Z-calibration probe, which sits at centre + 40 mm, onto the last tip
column, where `moveDownUntilPress()` presses hard enough to seat a tip.

Now bounded: give up after 8 mm (`stair_search_max_travel`, near the width of
the pipette end), shift the start 4 mm the other way, and rescan, at most 5 times
before raising `CalibrationScanError`. Raising is deliberate — the alternative is
recording a wrong centre that looks entirely plausible. `calibrate.py` catches
it, homes and exits non-zero.

Second fault: the scan is seeded from the stored centre, which can be
arbitrarily stale. `seedRackCenterFromReference()` now moves the tips centre with
the freshly measured samples rack.

16 mocked tests cover both, checked against mutated implementations to confirm
they fail when the fix is removed. Confirmed on the machine afterwards: it
stopped at exactly 8.000 mm, backed off, and recovered the edge at 23.420 — the
clean calibration found the same edge at 23.395, so the backstep path returns
the same answer to within 25 µm.

**The physical test could not fail correctly at first.** It started 2 mm outside
the nominal edge, but the nozzle keeps contact until its centre passes the edge
by about its own radius — measured 2.2 mm — so it was still resting on the rack
and found the edge immediately. Starting 5 mm out fixed it. The mocked tests
missed this because a simulated deck has no nozzle width.

`tips.json` was corrupted by the failed run and restored from backup; the
corrupted file is kept as `calibration_backup_20260807_2114/tips.json.FAILED_RUN`.

## 2026-08-07, 21:15 CDT — robot physically operates

First confirmed end-to-end run after bringing the machine back up: both
controllers talk, the robot homes, all axes move to commanded coordinates, and
both servos actuate. Everything worked as expected, verified physically at the
machine and not just from the position registers.

**Motion test.** `motion_test.py` (new), eight steps, all passing:

1. `ber.home()` — the top-level homing call.
2. X and Y to 100 mm, simultaneously via `moveXY()`.
3. Z to 50 mm.
4. Plunger (A) to 10 mm.
5. Magnets engaged (angle 11.2), held, disengaged (angle 5.2), rack servo off.
6. Plunger to 0 mm.
7. `dumpTip()` — tip ejector actuated at the current position.
8. Plunger back to 10 mm.

Final position read back exactly: X 100.00, Y 100.00, Z 50.00, A 10.00.

Notes on the choices, for next time:

- Z was 100 on the first run, which sat lower over the deck than intended;
  changed to 50. At Z=50 the clearance is ~97 mm bare-nozzle, ~55 mm with a tip.
- Magnets use `moveMagnetsTowardsTube()` / `moveMagnetsAway()` with
  `poweroff=False`, then a single `rackPowerOff()`, so the servo stays energised
  across the hold rather than being cut after each move. Note
  `rackMoveMagnetsAngle()` already sleeps 1.5 s per move, so the real dwell
  against the tubes is the script's hold plus that.
- Tip ejection uses `dumpTip()`, which acts at the current XYZ. The wrappers
  `dumpTipToWaste()` and `dumpTipToPosition()` drive the robot to a rack first,
  and `returnTipBack()` fails outright when no tip was ever picked up
  (`last_tip_coord` is None). `dumpTip()` leaves the plunger at 1, not 0.

The second run started from where the first parked the machine (100/100/100),
so homing had real distance to cover on every axis and still zeroed correctly —
better evidence than the first run, which started at 0,0,0,0.

**Both boards identified and answering.** `hello_robot.py` (new, read-only):

- Smoothieboard on COM3 — Smoothieware `edge-0565b13`, built Jun 19 2021,
  LPC1769 @ 120 MHz, 5 axes. Reports `Idle`.
- Load cell Arduino on COM10 — answers `Bernie's load cells controller`.
  Both HX711s live: readings wander in a ±0.3 band around zero, against
  decision thresholds of 100–500, so signal-to-noise is not a concern.

`getPosition()`'s parsing of the `?` reply was checked against this firmware
and still matches.

**Two things that had to be fixed to get here.**

1. No Python environment existed — no venv, and no dependencies in any conda
   env. Recreated `.venv` at the repo root per requirements.txt. This is now
   documented in CLAUDE.md and README.md so it does not come up again.
2. The load cell Arduino was invisible: it uses a Silicon Labs **CP2104**
   USB-UART bridge, and Windows had no CP210x driver (Device Manager code 28).
   Arduino IDE 2.x does not ship one. Fixed by installing
   `Silicon Laboratories Inc. - Ports - 11.2.0.167` from Windows Update, after
   which the board appeared as COM10.

**Resolved: the `A_min:1` endstop reading.** M119 showed the plunger endstop
triggered while X/Y/Z were not. It was simply the plunger parked on its switch,
not a fault — after the run it reads `A_min:0` with A at 10 mm.

### Open items found along the way

- **Homing order is enforced by config, not code.** `robotHome()` sends a bare
  `$H` and relies on `homing_order ZXYA` in the Smoothieboard config (verified
  present in the repo copy *and* on the board's SD card). Z-first is therefore
  correct today, but comment out or lose that one line — reflash, stock config —
  and `$H` homes all four axes simultaneously, driving the pipette across the
  deck. Proposed fix: have `robotHome()` sequence explicitly (`G28.2 Z`,
  `G28.2 X Y`, `G28.2 A`), which is safe under either config state. Still not
  applied. (`bernielib.py` was untouched when this was written; it has since been
  changed for the edge scan bounds, but not for homing.)
- **`writeAndWaitCartesian` can outrun long commands.** It waits for `ok` with
  the 5 s default in `_readUntilMatch`. Confirmed on the board with a `G4`
  dwell: an 8 s command times out at 5.00 s, returns `None`, and both `ok`s then
  arrive together, leaving replies offset by one. `?` is answered immediately
  even while the board is busy, so `getPosition()` can return a mid-motion
  coordinate when the preceding `M400` has timed out. It did not bite during
  today's run only because homing finished inside 5 s — a longer traverse
  (Y travels up to 322 mm) would trigger it.
- **`home(part=...)` falls through to a full home on any unrecognised value.**
  Only `'robot'`, `'pipette'` and `'magrack'` are matched; `'all'`, a typo, or
  anything else lands in the `else` branch and moves every axis.
- **Firmware: `T L` / `T R` are unreachable** in `firmware_arduino/bernie.ino`.
  `strtok` splits the input on spaces, so `command` is only ever `T`, which
  matches the tare-both branch first. Taring a single load cell has never
  worked. Harmless — bernielib only calls `tareAll()`.

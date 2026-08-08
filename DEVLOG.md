# Bernie dev log

Running record of work on the robot and the library. Newest entry first.
Ongoing tasks live in [general_todo.txt](general_todo.txt); this file is what
happened and when.

---

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
  `G28.2 X Y`, `G28.2 A`), which is safe under either config state. Not applied;
  `bernielib.py` is unchanged.
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

# Coordinated wall-wash experiment

**Status:** RUN 3 COMPLETED — controller sequence passed; operator observation pending
**Prepared:** 2026-08-23
**Code:** commit `afec2dc`, branch `hardware-bringup` — see
[code_version.txt](code_version.txt)

## Question

Can the installed Smoothieware motion planner move the carriage and pipette
plunger together, so the elution liquid is dispensed continuously while the tip
traces the side of an Eppendorf tube?

BernieLib now exposes this as `robot.moveCoordinated()`. It emits one absolute
`G1` block containing any requested X, Y, Z and A coordinates. Intermediate
waypoints are sent without `M400`; the final waypoint adds `M400` and then powers
off A. This lets the firmware queue the entire wall-wash path instead of forcing
the old move, dispense, move, dispense sequence to stop between every action.

`purify.py` is deliberately not changed by this experiment.

## Revision 3 preconditions

- Put one **empty** Eppendorf tube in purification position 0. In BernieLib
  coordinates that is samples-rack column 1, row 0.
- Reagent position 2 (reagents-rack column 0, row 2) must contain the yellow
  liquid in a 25 mL bottle. The script records it as starting at 25 mL and takes
  30 uL.
- Reagent position 1 (column 0, row 1) must contain the 25 mL liquid-waste
  bottle with room for this test's 30 uL.
- All tips must physically be present, as stated for this test. The script uses
  `pickUpNextTip()`, so also inspect that the first well listed in `tips.json`
  really contains a tip. Unit tests can refill the software inventory without
  refilling the physical rack.
- Empty or make room in the tip-waste container.
- Use the calibrated deck represented by the JSON settings in the repository
  root. Stand at the robot with the emergency stop reachable.
- Run from the repository root with the project's `.venv` Python.

The tube begins empty. The script seeds it with 30 uL from the yellow reagent,
then performs three complete aspirate-and-wall-wash repetitions. Each repetition
aspirates only 20 uL in one stroke just above the bottom, intentionally leaving
10 uL behind. The bottom is probed only for the first repetition if it has not
already been calibrated; repetitions 2 and 3 reuse that coordinate.

## Exact motion under test

After each aspiration, the tip first rises vertically at the tube centre to 24 mm
below the rim. It then moves sideways to X +3.000 mm without dispensing. Only
after those two movements does the coordinated dispense begin. X is relative to
the centre of position 0; Z is relative to the tube top; A is calculated from the
live volume-to-plunger calibration.

| Stage | X offset | Z below top | Cumulative 20 uL dispense |
|---|---:|---:|---:|
| Approach vertically, then sideways | +3.000 mm | 24 mm | 0 uL |
| Downward segment 1 | +3.000 mm | 28 mm | 6.67 uL |
| Downward segment 2 | +2.371 mm | 32 mm | 13.33 uL |
| Downward segment 3 | +1.742 mm | 36 mm | 20 uL |

The three downward `G1 X... Y... Z... A... F600` blocks are queued without a
sleep or `M400` between them. One `M400` follows segment 3. The tip then moves
inward to the tube centre at the lower Z and retracts there, so it never rises up
the pellet-bearing tapered wall and is out of the liquid before the next cycle
pre-positions the plunger. This complete cycle is performed three times.
Smoothieware uses the one feed rate for the combined XYZ/A path; it does not
provide an independent A-axis rate inside the block.

## Script sequence

1. Home once to establish safe absolute coordinates.
2. Pick up the next tip from the full tip rack.
3. Raise another 30 mm immediately after pickup, before any lateral travel, to
   clear an installed 25 mL reagent bottle.
4. Transfer 30 uL from yellow reagent position 2 into empty tube position 0.
5. Aspirate 20 uL at one fixed position just above the bottom, using one plunger
   stroke and leaving 10 uL in tube 0.
6. Rise at the centre, move to the upper wall, and dispense while moving downward
   and inward over three coordinated segments.
7. Repeat steps 5–6 three times total.
8. Aspirate tube 0 dry and dispense the liquid into liquid-waste reagent position 1.
9. Explicitly retreat to global safe Z `50` before any horizontal movement away
   from the 25 mL liquid-waste tube.
10. Drop the tip into the separate tip-waste container.
11. Home and power down the steppers.

For each repetition, timing starts immediately before the single-position
aspiration call and ends when the final coordinated dispense's `M400` completes,
before recenter/retract. The script reports all three durations, their mean, and
the total interval from the first aspiration start through the third dispense.
Wash 1 includes a one-time bottom-probe cost when calibration is absent. A JSON
copy is written to `data/wall_wash_timings_<run-id>.json`.

If an exception occurs after pickup starts, cleanup conservatively assumes a tip
may be attached, attempts to discard it into the waste, then homes and closes the
ports.

## Running it later

Without the confirmation flag the script only prints the plan and does not
construct a robot object:

```powershell
.\.venv\Scripts\python.exe experiments\20260823_coordinated_wall_wash\scripts\physical_experiment_coordinated_wall_wash.py
```

Run 1 used the explicit hardware gate below, but its frozen script predates the
revision described above:

```powershell
.\.venv\Scripts\python.exe -u experiments\20260823_coordinated_wall_wash\scripts\physical_experiment_coordinated_wall_wash.py --move-the-robot 2>&1 | Tee-Object experiments\20260823_coordinated_wall_wash\logs\run1_console.txt
```

Run 2 used the previous revised script with the following command:

```powershell
.\.venv\Scripts\python.exe -u experiments\20260823_coordinated_wall_wash\scripts\physical_experiment_coordinated_wall_wash.py --move-the-robot 2>&1 | Tee-Object experiments\20260823_coordinated_wall_wash\logs\run2_console.txt
```

Run 3 used revision 3 with this command:

```powershell
.\.venv\Scripts\python.exe -u experiments\20260823_coordinated_wall_wash\scripts\physical_experiment_coordinated_wall_wash.py --move-the-robot 2>&1 | Tee-Object experiments\20260823_coordinated_wall_wash\logs\run3_console.txt
```

Immediately before connecting, the script copies every JSON settings file it
will read into a timestamped folder under `configs/`, and freezes the executed
script plus `bernielib.py`, `samples.py`, and `general.py` under
`scripts/snapshots/`. Its per-run sample state is written under `data/`.

## Pass criteria

- The extra 30 mm lift makes the tipped nozzle visibly clear the installed 25 mL
  reagent bottles before lateral travel.
- Exactly 30 uL of yellow liquid reaches tube 0 before wall washing starts.
- Three complete wall-wash repetitions occur.
- Every wash uses one 20 uL aspiration stroke at one fixed bottom position; no
  multi-side low-volume aspiration sequence occurs.
- Each repetition rises at the tube centre, approaches the upper wall without
  dispensing, then follows all three downward segments continuously.
- Liquid is visibly expelled while XYZ is moving, rather than only after each
  carriage movement finishes.
- The tip never moves upward along the tapered wall and does not scrape the
  pellet location.
- Tube 0 ends empty, its liquid reaches reagent-position-1 liquid waste, the tip
  reaches tip waste, and final homing completes normally.
- After dispensing into liquid waste, Z reaches absolute `50` before the robot
  travels horizontally toward tip waste.
- The console and timing JSON report three individual wash durations, their
  mean, and first-aspiration-to-last-dispense total time.

## Results

### Run 1 — 2026-08-23 23:42:52

The gated script exited with code 0 and completed the requested software sequence:

- homed before pickup
- picked software-inventory tip `[0,0]`
- aspirated 30 uL from position 0; the bottom probe recorded Z `135.525`
- queued all four coordinated XYZ/A targets and waited after waypoint 4
- invoked the tip-waste routine
- invoked final home and closed both ports

One controller acknowledgement timed out for 5 seconds during final homing. The
script continued because the existing communication layer reports that timeout
as a warning rather than an exception. A separate read-only controller query
immediately afterwards returned `(X, Y, Z, A) = (0.0, 0.0, 0.0, 0.0)`, confirming
that the robot was at home despite the missing acknowledgement.

The persisted state agrees with the sequence: position 0 was restored to 30 uL,
tip `[0,0]` was consumed, the next software-inventory tip is `[0,1]`, and 95 tips
remain listed.

Evidence:

- [`logs/run1_console.txt`](logs/run1_console.txt) — complete hardware-run output
- [`logs/run1_position_check.txt`](logs/run1_position_check.txt) — post-run controller position
- [`configs/20260823_234252/`](configs/20260823_234252/) — settings immediately before connection
- [`scripts/snapshots/20260823_234252/`](scripts/snapshots/20260823_234252/) — executed code snapshot
- [`data/wall_wash_sample_20260823_234252.json`](data/wall_wash_sample_20260823_234252.json) — tube state

#### Operator feedback

- Tube 0 was deliberately empty, so run 1 could not show whether liquid was
  dispensed during motion.
- The tipped nozzle did not rise high enough after pickup. With the 25 mL bottle
  installed it would have collided; approximately 30 mm more clearance is needed.
- The path travelled upward along the taper after aspiration. That direction is
  rejected because it can scrape and displace the bead pellet instead of washing
  it downward.

Revision 2 directly incorporates all three observations: it adds the 30 mm
post-pickup lift, supplies visible yellow liquid from reagent position 2, and
changes each wall wash to a non-dispensing high approach followed by a downward
coordinated dispense. It also repeats that wash three times and removes the final
liquid to reagent-position-1 waste.

### Run 2 — 2026-08-24 00:09:43

The revised gated script exited with code 0 and completed its entire controller
sequence:

- homed and picked software-inventory tip `[0,1]`
- raised Z an additional 30 mm before travelling to the reagent rack
- transferred 30 uL from yellow reagent position 2 to empty tube 0
- completed three wall-wash repetitions, each with a vertical centre rise, a
  non-dispensing sideways approach, and three queued downward XYZ/A segments
- recentered and retracted vertically after every downward wash
- aspirated tube 0 dry and dispensed into reagent-position-1 liquid waste
- invoked the tip-waste routine and final home

Persisted liquid state matches the intended transfer: tube 0 is `0 uL`, the
yellow source changed from `25000` to `24970 uL`, and liquid waste is `30 uL`.
The bottom probe recorded tube-0 Z `135.625`. Tip `[0,1]` was consumed, `[0,2]`
is next, and 94 tips remain in software inventory.

As in run 1, one acknowledgement timed out for 5 seconds during final home. The
script exited normally, and an immediate read-only controller query returned
`(X, Y, Z, A) = (0.0, 0.0, 0.0, 0.0)`, confirming final home.

Run 2 evidence:

- [`logs/run2_console.txt`](logs/run2_console.txt) — complete hardware-run output
- [`logs/run2_position_check.txt`](logs/run2_position_check.txt) — post-run controller position
- [`configs/20260824_000943/`](configs/20260824_000943/) — seven settings inputs
- [`scripts/snapshots/20260824_000943/`](scripts/snapshots/20260824_000943/) — executed code
- [`data/wall_wash_sample_20260824_000943.json`](data/wall_wash_sample_20260824_000943.json) — emptied tube 0
- [`data/yellow_reagent_20260824_000943.json`](data/yellow_reagent_20260824_000943.json) — yellow-source state
- [`data/liquid_waste_20260824_000943.json`](data/liquid_waste_20260824_000943.json) — liquid-waste state

#### Operator feedback

- All pipetting was performed correctly and the wall-wash behaviour looked as
  expected.
- After dispensing into liquid waste, the script did not retreat to its requested
  safe height before travelling. The tip contacted the 25 mL tube wall. The
  contact was not critical, but the path must not be repeated.
- Aspirating all 30 uL for every wash took too long because `uptakeLiquid()` used
  its full low-volume routine: several partial aspirations at different tube
  positions.

Revision 3 fixes the clearance issue with an explicit `move(z=50)` immediately
after liquid-waste dispensing and the same safe retreat in exception cleanup.
It adds `bernielib.robot.uptakeLiquidSinglePosition()`: one 20 uL stroke at a
single coordinate just above bottom, leaving 10 uL in the tube. It also adds
monotonic timing around each aspiration-through-dispense interval and persists
the calculated durations. Run 2 cannot be timed accurately after the fact because
its log did not record timestamps at those boundaries; revision 3 will measure
them directly. Revision 3 was subsequently executed as run 3 below.

### Run 3 — 2026-08-24 00:37:43

The revision-3 script exited with code 0 and completed the full controller
sequence. It used software-inventory tip `[0,2]`, performed all three one-stroke
20 uL aspirations and descending dispenses, emptied tube 0 into liquid waste,
explicitly moved to absolute Z `50` after the liquid-waste dispense, invoked tip
disposal, and homed.

#### Measured wall-wash time

Each individual interval begins immediately before its 20 uL single-position
aspiration and ends when the last downward dispense segment's `M400` completes.

| Wash | Time | Interpretation |
|---|---:|---|
| 1 | 8.763 s | Includes the one-time tube-bottom probe |
| 2 | 1.835 s | Calibrated steady-state wash |
| 3 | 1.837 s | Calibrated steady-state wash |
| Mean, all three | 4.145 s | Skewed by the initial calibration |
| Mean, washes 2–3 | **1.836 s** | Representative repeated-wash time |

The total from the first aspiration start through the third final dispense was
**12.796 seconds**. The one-time first-wash penalty relative to the steady-state
mean was approximately **6.927 seconds**. About 0.361 seconds of the total was
between-wash recenter/retract overhead, which is intentionally outside each
individual aspiration-to-dispense interval.

Persisted liquid state matches the request: tube 0 is `0 uL`, yellow source is
`24970 uL`, and reagent-position-1 liquid waste is `30 uL`. Tube-bottom Z was
measured as `135.825`. Tip `[0,2]` was consumed, `[0,3]` is next, and 93 tips
remain in software inventory.

The recurring final-home acknowledgement timed out once for 5 seconds. The
script exited normally, and the immediate read-only query again returned
`(X, Y, Z, A) = (0.0, 0.0, 0.0, 0.0)`.

Run 3 evidence:

- [`logs/run3_console.txt`](logs/run3_console.txt) — complete hardware-run output
- [`logs/run3_position_check.txt`](logs/run3_position_check.txt) — final controller position
- [`data/wall_wash_timings_20260824_003743.json`](data/wall_wash_timings_20260824_003743.json) — raw timing values
- [`data/wall_wash_sample_20260824_003743.json`](data/wall_wash_sample_20260824_003743.json) — emptied tube 0
- [`data/yellow_reagent_20260824_003743.json`](data/yellow_reagent_20260824_003743.json) — yellow-source state
- [`data/liquid_waste_20260824_003743.json`](data/liquid_waste_20260824_003743.json) — liquid-waste state
- [`configs/20260824_003743/`](configs/20260824_003743/) — settings inputs
- [`scripts/snapshots/20260824_003743/`](scripts/snapshots/20260824_003743/) — executed code

Controller output confirms that the Z=50 retreat command was completed before
tip disposal, but direct operator observation is still needed to confirm physical
tube-wall clearance, the appearance of the shortened aspiration, continued
wash quality, and physical tip disposal.

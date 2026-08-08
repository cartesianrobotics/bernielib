# Sideways edge finding — experiment record, 2026-08-08

Raw data from the experiments in [`../physical_tests/`](../physical_tests/), kept
so the conclusions below can be re-checked rather than taken on trust. One of
them was wrong for several hours, and the data is how that was caught.

## Why this was run

Calibration finds a rack edge by tapping downwards: press the nozzle onto the
rack, step sideways, press again, and watch for the step where the surface drops
away. Every one of those lateral steps costs a full descend-until-press cycle of
many small Z moves, and that is where calibration spends its time.

A sideways touch would need **one** approach instead. So: do the load cells,
which are only ever used pressing straight down, register a horizontal contact
at all — and if they do, does the edge they report agree with the tapping method?

## What was found

**1. The cells see a sideways touch very clearly.** At contact one increment was
93× the previous one. Detection sensitivity was never the difficulty.

**2. But they also drift with carriage position, with nothing touched.** Both
cells ramp steadily as soon as the carriage moves — the right about 2.7× as far
as the left and in the opposite direction, the ratio holding constant. This was
confirmed by running 20 mm *above* the rack where contact is impossible
(`..._side_load_control.csv`) and by watching the machine: 2–3 mm still remained
before the nozzle could touch anything. It is the mount reacting to the
carriage's own geometry changing, not contact.

Any rule based on how far a reading has moved from its baseline fires on this
drift every time. The fix is to measure the drift first, at the same positions
but above the rack, and subtract it. After subtraction the signal stays inside
±1.6 across several mm of approach, then jumps by a factor of ~20–90 on contact.

**3. Contact is a step change, not a runaway.** One huge increment, then
increments that stay large but stop growing, with ratios back near 1. An early
rule asking for four consecutive doublings therefore never fired — contact does
not do that. A single large ratio is the signature.

**4. Contact magnitude varies far too much for a fixed threshold.** Across four
edges the corrected signal at contact was 11, 91, 4.4 and 67. A cutoff of 70
caught one edge in four and let the back Y edge run 3 mm into the rack
undetected. Detection is now scaled to the flat band each run measures for
itself: `max(3.0, 3 × the largest signal in the first few steps)`. Validated
against all four recorded datasets before being used.

**5. The method agrees with Z-tapping.** Final figures, all four edges of the
samples rack:

| Edge | Sideways | Z-tapping | Difference |
|---|---|---|---|
| right (X low) | 5.100 | 5.200 | −0.100 |
| left (X high) | 168.900 | 168.600 | +0.300 |
| front (Y low) | 9.200 | 9.500 | −0.300 |
| back (Y high) | 194.500 | 194.700 | −0.200 |

Repeatability within a run is 0.00–0.06 mm across three independent
determinations per edge; run to run it is 0.00–0.10 mm.

## The wrong left-X measurements, and why

**This is the part worth reading before trusting any number above.**

The left X edge first measured **169.700**, disagreeing with Z-tapping by
**+1.100 mm** while the other three edges agreed within 0.3 mm. It reproduced
three times, at +1.133, +1.100 and +1.100, which made it look like a solid
finding rather than a fault.

It was not a finding. **The approach started at X=172.90, which fouls the far end
of X travel.** The carriage was seen hitting it. Somewhere in that first move it
lost roughly 0.8 mm of steps, and because every subsequent position is measured
from there, the entire run read high by that amount.

Backing the start off proved it:

| Start X | Measured edge | vs Z-tapping |
|---|---|---|
| 172.90 | 169.700 | +1.100 |
| 171.40 | 168.900 | +0.300 |
| 170.40 | 168.967 | +0.367 |

The first 1.5 mm of backing off moved the reading 0.800 mm. The next 1.0 mm
moved it 0.067 mm — inside the ordinary scatter. So the interference is gone by
171.40 and the reading has converged. Two independent signs point the same way:
the flat band on that side fell from 3.594 to 3.096 to 2.026 as the start moved
back, and the pre-contact readings became smooth.

`USABLE_MAX['X'] = 171.4` in the experiment script now caps the start, so a plain
`--side left` reproduces the good configuration without anyone having to
remember. `robot.json` still says `x_max: 189`, which is not reachable in
practice — worth correcting there if anything else relies on it.

### Conclusions withdrawn because of this

Stated confidently at the time, and wrong:

- That something is **physically proud by ~1.1 mm on the left-hand wall** of the
  samples rack, invisible to the top scan. There is no evidence for it. Nobody
  should go looking for that feature.
- That the **X span is 1.200 mm wider and the centre 0.500 mm off** compared with
  Z-tapping. Both were the step loss, halved and doubled respectively — exactly
  the signature a single displaced edge produces, which is why it looked
  coherent.

### The conclusion that survives

**Wall draft is ruled out.** The suspicion was that probing 5 mm below the top
plane catches an outward taper the top scan cannot see. If so, both axes would
read wide. Y agreed with Z-tapping on span to 0.100–0.133 mm across three
separate runs, at the same depth with the same nozzle. That reasoning rests only
on the Y measurements, which the X-axis interference never touched.

A residual pattern remains and is unexplained: three edges sit at −0.1 to −0.3
and the left at +0.37, i.e. a small systematic offset of about −0.2 between the
methods plus roughly 0.5 mm specific to the left edge. It is a fifth the size of
the artifact above and no longer stands out, but it did survive the fix.

## Datasets

| File | Contents |
|---|---|
| `20260808_014825_side_load.csv` | First sideways walk, 5 mm below the plane. Stopped after 4 steps; drift discovered. |
| `20260808_015712_side_load_control.csv` | Control, 20 mm **above** the plane — contact impossible. Same drift; proves it is not contact. |
| `20260808_015844_side_load.csv` | Second walk. Contact at X=5.5, increment ratio 93×. Force backstop stopped it. |
| `20260808_021425_side_edge_find.csv` | First background-subtracted edge find, right X. Three crossings at 5.100. |
| `20260808_022705_side_edge_find.csv` | Left X, **start 172.90 — contaminated by the end-of-travel interference**. 169.733. |
| `20260808_023906_side_edge_find.csv` | Front and back Y. Front good; back contacted but the detector missed it. |
| `20260808_024542_side_edge_find.csv` | Back Y re-run with the band detector. 194.633. |
| `20260808_025343_side_edge_find.csv` | All four edges, travelling between sides at Z=0. |
| `20260808_030716_side_edge_find.csv` | All four again, travelling at the safe height. Measurements unchanged — the travel path does not affect the reading. |
| `20260808_031211_side_edge_find.csv` | Left X, **start 171.40 — the fix**. 168.900. |
| `20260808_031611_side_edge_find.csv` | Left X, start 170.40. 168.967 — converged, so 171.40 is enough. |

`*_console.txt` files are the full session output for the runs that produced
them. Columns in the CSVs: raw readings, deviation from that pass's baseline,
the background at that position, the corrected value, and the combined signal.

## Reproducing

From the repository root, with the tube racks calibrated recently (the
comparison figures are read from the newest report in `../calibration_reports/`):

```
.venv\Scripts\python.exe physical_tests\physical_experiment_side_edge_find.py --side right,left,front,back
.venv\Scripts\python.exe physical_tests\physical_experiment_side_edge_find.py --side right,left,front,back --move-the-robot
```

Without `--move-the-robot` it prints the plan and moves nothing. Each run writes
a new timestamped CSV, so nothing here is overwritten.

## Is it usable for calibration?

Not yet as a drop-in. It agrees to 0.3 mm and repeats to 0.06 mm, which is
promising, and it is much faster per edge. Open questions: how far one background
pass generalises across positions and heights, where the residual ~0.2 mm offset
comes from, and whether other racks behave like this one. Only the samples rack
has been tested.

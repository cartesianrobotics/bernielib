# Settings snapshots

The gated hardware script creates one timestamped subfolder here immediately
before it constructs `bernielib.robot()`. Revision 2 reads seven JSON settings
files, adding `25mL.json` for the yellow-source and liquid-waste bottles. A
matching code snapshot is created under
`scripts/snapshots/`.

Run 1 is recorded in `20260823_234252/`; that older version read six settings
files and did not use a 25 mL source or liquid-waste bottle.

Run 2 is recorded in `20260824_000943/` and contains all seven revision-2
settings inputs.

Run 3 is recorded in `20260824_003743/` and contains all seven revision-3
settings inputs.

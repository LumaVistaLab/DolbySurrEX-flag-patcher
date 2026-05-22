# Dolby Surround EX Flag Patcher

This repository contains a small Python patcher for DMPS Blu-ray DD+ / E-AC-3
Atmos `.eb3` bitstreams where the AC-3 core should advertise Dolby Surround EX.

## Observed Bitstream Structure

Both sample files are Blu-ray-profile DD+ Atmos streams. Each 1536-sample access
unit is 6656 bytes:

- 2560-byte AC-3 core syncframe, 640 kb/s
- 4096-byte E-AC-3 dependent/JOC syncframe, 1024 kb/s

The relevant flag is in the AC-3 core extended bitstream information:

```text
bsid=6
acmod=7
lfeon=1
xbsi1e=1
dmixmod=1
xbsi2e=1
dsurexmod=<target>
```

`Escape.eb3` has `dsurexmod=2` in every AC-3 core frame, which MediaInfo reports
as `Format settings: Dolby Surround EX`.

`Sol Levante.eb3` has `dsurexmod=0` in every AC-3 core frame. The patcher sets
that two-bit field to `2` and recomputes the AC-3 CRC words.

For the current samples, `dsurexmod` starts at bit 90 of each AC-3 core frame.
At byte level this changes core byte 11 from `0x40` to `0x60`, plus the AC-3
CRC1 word at core bytes 2-3. The E-AC-3 dependent/JOC frames are not modified.

## Usage

Scan only:

```powershell
python .\patch_dsur_ex.py --check "Sol Levante.eb3"
```

Patch to a new file:

```powershell
python .\patch_dsur_ex.py "Sol Levante.eb3" "Sol Levante.dsur-ex.eb3"
```

The tool refuses to patch if an AC-3 core frame does not match the expected
`bsid=6`, `acmod=7`, `lfeon=1`, `xbsi2e=1` structure, or if input AC-3 CRCs are
already invalid.

## Verification Run

Current local verification:

```text
Escape.eb3:
  AC-3 core frames: 7013
  E-AC-3 dependent frames: 7013
  dsurexmod counts: {2: 7013}
  AC-3 CRC mismatches: 0

Sol Levante.eb3:
  AC-3 core frames: 8222
  E-AC-3 dependent frames: 8222
  dsurexmod counts: {0: 8222}
  AC-3 CRC mismatches: 0

Sol Levante.dsur-ex.eb3:
  AC-3 core frames: 8222
  E-AC-3 dependent frames: 8222
  dsurexmod counts: {2: 8222}
  AC-3 CRC mismatches: 0
```

MediaInfo reports `Format settings: Dolby Surround EX` for
`Sol Levante.dsur-ex.eb3`.

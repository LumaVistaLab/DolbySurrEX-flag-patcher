# Dolby Surround EX Flag Patcher

This repository contains a Python patcher for a specific Dolby Media Producer
Suite 2.0 output case: Blu-ray Dolby Digital Plus with Dolby Atmos `.eb3`
bitstreams whose 7.1 Lrs/Rrs audio core was authored with a `5.1 Dolby PLIIx`
7.1-to-5.1 downmix, but whose AC-3 core metadata does not advertise Dolby
Surround EX.

The tool patches the AC-3 core `dsurexmod` field to the value MediaInfo reports
as `Format settings: Dolby Surround EX`, then recomputes the AC-3 CRC words.

## Use Case and Prerequisite

Use this patcher only when all of the following are true:

- The source is a Blu-ray-profile Dolby Digital Plus / E-AC-3 `.eb3` bitstream,
  with or without Dolby Atmos.
- The audio core channel configuration is `7.1 - L,R,C,LFE,Ls,Rs,Lrs,Rrs`.
- The DMPS job used `7.1 to 5.1 Downmix: 5.1 Dolby PLIIx`, not `5.1 Standard`.
- The goal is to mark the backward-compatible 5.1 presentation as containing
  matrix-encoded rear surround information.

The `5.1 Dolby PLIIx` prerequisite is important. Dolby's manual describes PLIIx
as a matrix system that can derive rear surround channels from 5.1 sources, and
it describes Dolby Digital Surround EX's bitstream flag as being repurposed to
indicate matrix-encoded rear surround signals in Dolby TrueHD, Dolby Digital
Plus, or Dolby Digital 5.1-channel presentations, including the 5.1 presentation
heard when a 7.1 bitstream is decoded on a 5.1-only system. See References [3]
and [4].

`Sol Levante.png` shows the DMPS v2.0 setup used for the sample output:

![DMPS v2.0 channel setup: 7.1 Lrs/Rrs core and 5.1 Dolby PLIIx downmix](Sol%20Levante.png)

Do not use this as a generic DD+ or Atmos repair tool. If the encode used
`5.1 Standard (Lo, Ro)` downmixing, setting the EX flag would misrepresent the
bitstream.

## Observed Bitstream Structure

Both sample files are Blu-ray-profile DD+ Atmos streams. Each 1536-sample access
unit is 6656 bytes:

- 2560-byte AC-3 core syncframe, 640 kb/s
- 4096-byte E-AC-3 dependent/JOC syncframe, 1024 kb/s

This matches the way DMPS presents Dolby Digital Plus Blu-ray jobs: a
backward-compatible audio core is selected on the Channels page, and for Atmos
DD+ bitstreams the 5.1 core is produced by rendering Atmos to 7.1, then
downmixing the four surround channels to the two 5.1 surround channels. The
manual lists `5.1 Dolby Standard (Lo, Ro)` and `5.1 Dolby PLIIx` as the relevant
choices. See References [1] and [2].

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

`Sol Levante.eb3` has `dsurexmod=0` in every AC-3 core frame. Because its DMPS
job used `5.1 Dolby PLIIx`, this repository treats `Escape.eb3` as the
reference writer behavior and patches `Sol Levante.eb3` to the same
`dsurexmod=2` state.

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

## References

[1] Dolby Media Encoder User's Manual, Section 4.1.3, "Selecting Source Material
(Encoding Configurations) for Encoding", printed p. 18 / PDF p. 28. For Dolby
Digital Plus with Dolby Atmos, the manual says the backward-compatible
presentation is set with `Audio Core Channel Configuration`.

[2] Dolby Media Encoder User's Manual, Section 4.1.4, "Setting the 5.1 Downmix
Type on the Channels Page", printed pp. 18-19 / PDF pp. 28-29, and Section 4.5,
"Creating a Dolby Digital Plus Bitstream with or without Dolby Atmos", printed
p. 33 / PDF p. 43. These sections state that the 5.1 core is produced by
rendering Atmos to 7.1 when needed and downmixing the 7.1 surround channels to
5.1, with `5.1 Dolby Standard (Lo, Ro)` and `5.1 Dolby PLIIx` as the choices.

[3] Dolby Media Encoder User's Manual, Section 11.11, "Dolby Pro Logic IIx",
printed pp. 94-95 / PDF pp. 104-105. This section defines PLIIx as a matrix
decoding system that derives rear surround channels, including 5.1-to-7.1
operation from independent Ls/Rs channels.

[4] Dolby Media Encoder User's Manual, Section 11.13, "Dolby Digital Surround
EX", printed p. 96 / PDF p. 106. This section explains that the EX bitstream
flag indicates matrix-encoded rear surround signals and is repurposed for Dolby
TrueHD, Dolby Digital Plus, and Dolby Digital 5.1 presentations, including the
5.1 presentation obtained from a 7.1 bitstream on a 5.1-capable system.

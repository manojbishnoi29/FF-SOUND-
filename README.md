# Craftland Custom SFX Pack

One replacement sound for Free Fire Craftland, prepared for in-game UID **2284575373**.

- Asset ID: **679001**
- Sound: `free_fire_fanny_tone`
- GitHub repository: [manojbishnoi29/FF-SOUND-](https://github.com/manojbishnoi29/FF-SOUND-) (public)
- Hosting branch: `arena/3449d202-ff-sound`

## Hosted payload URLs

- WebGL: [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/WebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/WebGL)
- NotWebGL: [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/NotWebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/NotWebGL)

These are the exact raw paths referenced by `Store/679001_1.bytes`. Payload files are extensionless by design.

## Files

- `679001/` — raw payloads used by the in-game descriptor.
- `Store/679001_1.bytes` — asset descriptor; refers to the hosted branch above.
- `2284575373/ResourceIndex.bytes` — resource index; keep the directory name as the UID.
- `Craftland_Custom_SFX_2284575373.zip` — install pack archive containing Store, UID index and payloads.
- `tooling/` — builder and its registry template for future sounds.

## Install

Extract the ZIP and copy `Store/` and `2284575373/` to:

```text
Android/data/com.dts.freefireth/files/Workshop/
```

For Free Fire MAX use `Android/data/com.dts.freefiremax/files/Workshop/`. Back up existing Workshop files first; this pack is intended to replace the previous sound set rather than merge with it.

## Add more sounds

Keep `craftland_soundpack_builder.py` and `editor_gen_template.bin` together. Install `imageio-ffmpeg`, then run the builder with this repository and the hosting branch, keeping `--start-id 679001` so this asset ID remains stable. New sounds should receive subsequent IDs. Rebuild the install files and upload every generated asset folder while preserving the asset-ID directory names.

## Verification / checksums

SHA-256 (hex):

| File | Bytes | SHA-256 |
|---|---:|---|
| `679001/WebGL` | 145,847 | `dc1352818130d3096912c2b890839feed45a66a45501f7542d70530ce1970b08` |
| `679001/NotWebGL` | 1,719,326 | `76e6d2263c1619c7132997b846b9b55ed630da7743aa10a5f18e1c246146c1de` |
| `Store/679001_1.bytes` | 2,361 | `ac817b7abcd6eb4050132bdc9aa2faafc12751d86ab97d366c55c6f7ca7d65a2` |
| `2284575373/ResourceIndex.bytes` | 817 | `a7d6cd2cd0806d0c7afe90dd60fdf7d26bd06f777b9bf08ca287db57db29b980` |
| `Craftland_Custom_SFX_2284575373.zip` | 1,868,389 | `307a1a2e139ab583b5ef58a6cdb2b395ad4fc6748021d648addf0dec5aeea6f6` |

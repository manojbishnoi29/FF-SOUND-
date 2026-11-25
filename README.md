# Craftland Custom SFX Pack

Free Fire Craftland sound pack for in-game UID **2284575373**. Public raw payloads are hosted in this repository.

- Repository: https://github.com/manojbishnoi29/FF-SOUND-
- Hosting branch: `arena/3449d202-ff-sound`

## Sounds and raw payloads

| Asset ID | Sound | WebGL | NotWebGL |
|---:|---|---|---|
| 679001 | `free_fire_fanny_tone` | [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/WebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/WebGL) | [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/NotWebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679001/NotWebGL) |
| 679002 | `Indila - Tourner Dans Le Vide (Slowed & Reverb)` | [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679002/WebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679002/WebGL) | [https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679002/NotWebGL](https://raw.githubusercontent.com/manojbishnoi29/FF-SOUND-/refs/heads/arena/3449d202-ff-sound/679002/NotWebGL) |

## Pack files

- `Store/679001_1.bytes` and `Store/679002_1.bytes` — asset descriptors.
- `2284575373/ResourceIndex.bytes` — UID index; keep this folder name unchanged.
- `Craftland_Custom_SFX_2284575373.zip` — install archive with both sounds and payloads.
- `tooling/` — builder and its template for future audio.

## Install

Extract the ZIP and copy `Store/` and `2284575373/` to:

```text
Android/data/com.dts.freefireth/files/Workshop/
```

For Free Fire MAX use `Android/data/com.dts.freefiremax/files/Workshop/`. Back up existing Workshop files before replacing them.

## Add future sounds

Use `tooling/craftland_soundpack_builder.py` with its adjacent `editor_gen_template.bin`. Keep the current sound sources in the input folder and use `--start-id 679001`, `--uid 2284575373`, and this hosting branch. Preserve existing asset IDs when rebuilding.

## SHA-256 checksums

| File | Bytes | SHA-256 |
|---|---:|---|
| `679001/WebGL` | 145,847 | `dc1352818130d3096912c2b890839feed45a66a45501f7542d70530ce1970b08` |
| `679001/NotWebGL` | 1,719,326 | `76e6d2263c1619c7132997b846b9b55ed630da7743aa10a5f18e1c246146c1de` |
| `679002/WebGL` | 3,085,632 | `e76353ada31cad7c1facad7c30b4fea9358f0417f495e3d1a84375c7e678fce9` |
| `679002/NotWebGL` | 41,712,116 | `cb33ea946bdabd3dd7704c98b43fe2724c2e250adc97c34dacadd8dc47ccb662` |
| `Store/679001_1.bytes` | 2,361 | `ac817b7abcd6eb4050132bdc9aa2faafc12751d86ab97d366c55c6f7ca7d65a2` |
| `Store/679002_1.bytes` | 2,759 | `390360d42879fd46deb7cb020e1ccf38b57716217048f61416697a814a4d18a1` |
| `2284575373/ResourceIndex.bytes` | 1,042 | `1bc0cba2c8ae0fe05305935b971ce14b0a424fabd490a22be2b8fad805fdadb6` |
| `Craftland_Custom_SFX_2284575373.zip` | 46,681,469 | `eb3c213bec46af5181fe639be525e01680fcaf7d792d8ff5f4d69c06da8fea3d` |

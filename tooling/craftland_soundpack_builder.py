#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Craftland Sound Pack Builder  (v2)
==================================
Apne Suno/other .wav sounds se Craftland Workshop pack banata hai:

    <out>/Store/<asset_id>_1.bytes      <- UGC resource descriptor (protobuf)
    <out>/UID/ResourceIndex.bytes       <- index (MS-NRBF / BinaryFormatter)
    <out>/upload/<asset_id>/WebGL       <- GitHub raw ke liye (MP4/AAC)
    <out>/upload/<asset_id>/NotWebGL    <- GitHub raw ke liye (FSB5 PCM16)

Payload format (Garena ka "VFS" container) bilkul reference pack jaisa:
    [64B VFS header][IDX block][gzip(vernum container)][dir entry][SFVE]
    vernum container = [header][audio bytes]
      WebGL    -> MP4 / AAC-LC 44.1kHz stereo
      NotWebGL -> FSB5 bank (PCM16)

Usage:
  python3 craftland_soundpack_builder.py --sounds ./sounds --repo USER/REPO \
      --branch main --out ./out --author "Your Name" --code "MYCODE"

Requires: imageio-ffmpeg (ffmpeg binary), nrbf (sirf verify ke liye).
"""

import argparse
import base64
import gzip
import hashlib
import json
import os
import random
import re
import shutil
import struct
import subprocess
import sys

# ---------------------------------------------------------------------------
# Constants / templates
# ---------------------------------------------------------------------------

APP_VERSION = "1.16.4179668"
SAMPLE_RATE = 44100
CHANNELS = 2
LIB_NAME = "Assembly-CSharp, Version=0.86.0.518, Culture=neutral, PublicKeyToken=null"
LIST_TYPE = ("System.Collections.Generic.List`1[[COW.Gameplay.UGC.UGCResourceIndexEntry, "
             "Assembly-CSharp, Version=0.86.0.518, Culture=neutral, PublicKeyToken=null]]")
ENTRY_TYPE = "COW.Gameplay.UGC.UGCResourceIndexEntry"

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "editor_gen_template.bin")

TEMPLATE_REPLACEMENTS = [
    ("b28uacqu7", "reg_id"),                      # 9 chars
    ("auI7sLeX", "namespace"),                   # 8 chars
    ("AutoWebglsp_YJ9F09jh", "package_suffix"),  # 20 chars
    ("rxYYTG+2p9j4wjxUlFJvze3S5Oc=", "version_md5"),  # 28 chars
]

ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def rand_str(n, alphabet=ALNUM):
    return "".join(random.choice(alphabet) for _ in range(n))


def rand_uuid():
    """8-8-12 lowercase alnum, reference jaisa."""
    low = "abcdefghijklmnopqrstuvwxyz0123456789"
    return f"{rand_str(8, low)}-{rand_str(8, low)}-{rand_str(12, low)}"


# ---------------------------------------------------------------------------
# Protobuf helpers
# ---------------------------------------------------------------------------

def varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def fvar(num, v):
    return varint((num << 3) | 0) + varint(v)


def fbytes(num, b):
    return varint((num << 3) | 2) + varint(len(b)) + b


def read_varint(b, i):
    shift = val = 0
    while True:
        x = b[i]
        i += 1
        val |= (x & 0x7F) << shift
        if not (x & 0x80):
            return val, i
        shift += 7


def parse_fields(b):
    i, out = 0, {}
    while i < len(b):
        tag, i = read_varint(b, i)
        num, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = read_varint(b, i)
            out[num] = v
        elif wt == 2:
            ln, i = read_varint(b, i)
            out[num] = b[i:i + ln]
            i += ln
        elif wt == 5:
            out[num] = b[i:i + 4]
            i += 4
        elif wt == 1:
            out[num] = b[i:i + 8]
            i += 8
        else:
            raise ValueError(f"unsupported wire type {wt}")
    return out


# ---------------------------------------------------------------------------
# FSB5 (FMOD SoundBank 5) - PCM16 writer
# ---------------------------------------------------------------------------

def build_fsb5_pcm16(pcm, channels=CHANNELS, frequency=SAMPLE_RATE, frames=None):
    """Raw interleaved PCM16 -> FSB5 bank (mode 2 = PCM16)."""
    if frames is None:
        frames = len(pcm) // (2 * channels)

    # sample header: uint64 bitfield + chunks
    raw = (1 << 0)              # next_chunk = 1
    raw |= (0 << 1)             # frequency code (0 -> FREQUENCY chunk use hoga)
    raw |= ((channels - 1) << 5)
    raw |= (0 << 6)             # dataOffset / 16
    raw |= (frames << 34)
    sh = bytearray(struct.pack("<Q", raw))
    # CHANNELS chunk (type 1, size 1)
    sh += struct.pack("<I", (1 << 0) | (1 << 1) | (1 << 25))
    sh += bytes([channels])
    # FREQUENCY chunk (type 2, size 4)
    sh += struct.pack("<I", (0 << 0) | (4 << 1) | (2 << 25))
    sh += struct.pack("<I", frequency)

    hdr = b"FSB5" + struct.pack("<6I", 1, 1, len(sh), 0, len(pcm), 2)
    hdr += struct.pack("<I", 1) + b"\x00" * 4   # unknown + 4B (8B field)
    hdr += b"\x00" * 16                          # hash
    hdr += b"\x00" * 8                           # dummy
    assert len(hdr) == 60, len(hdr)
    return hdr + bytes(sh) + pcm


# ---------------------------------------------------------------------------
# vernum container
# ---------------------------------------------------------------------------

def build_vernum(name, channels, sample_rate, frames, payload):
    """Garena ka 'vernum' versioned-asset wrapper."""
    nb = name.encode("utf-8")
    name_len = len(nb) + 1
    header_len = 18 + name_len + 44

    out = bytearray()
    out += b"vernum"
    out += struct.pack("<I", 1)                 # version
    out += struct.pack("<I", name_len)
    out += struct.pack("<I", 0)
    out += nb + b"\x00"
    out += struct.pack("<i", channels)
    out += struct.pack("<i", 0)
    out += struct.pack("<i", 32)
    out += struct.pack("<i", 0)
    out += struct.pack("<q", frames)            # int64 frame count
    out += struct.pack("<f", float(sample_rate))
    out += struct.pack("<i", header_len)
    out += struct.pack("<i", 0)
    out += struct.pack("<i", len(payload))
    out += struct.pack("<i", 0)
    out += payload
    assert len(out) == header_len + len(payload)
    return bytes(out)


# ---------------------------------------------------------------------------
# VFS container
# ---------------------------------------------------------------------------

def gzip_bytes(data, level=6):
    """Deterministic gzip: header mtime=0, OS=0x0a (reference jaisa)."""
    co = zlib_obj = __import__("zlib")
    compressor = co.compressobj(level, co.DEFLATED, -15)
    body = compressor.compress(data) + compressor.flush()
    crc = co.crc32(data) & 0xFFFFFFFF
    return (b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0a" + body
            + struct.pack("<II", crc, len(data) & 0xFFFFFFFF))


def build_vfs(vernum_bytes, entry_name, source_path):
    """VFS package: 64B header + IDX block + gzip(vernum) + dir entry + SFVE."""
    gz = gzip_bytes(vernum_bytes)

    # directory entry (fixed 128-byte source-name buffer)
    src = source_path.encode("utf-8")[:127]
    entry = bytearray()
    entry += struct.pack("<I", 1)
    entry += struct.pack("<I", len(entry_name))
    entry += entry_name.encode("utf-8")
    entry += struct.pack("<I", 5)
    entry += struct.pack("<I", 1)
    entry += struct.pack("<Q", 92)                 # gzip data offset
    entry += struct.pack("<I", len(gz))
    entry += struct.pack("<I", len(vernum_bytes))
    entry += struct.pack("<I", 0)
    entry += src + b"\x00" * (128 - len(src))
    entry += b"SFVE"
    assert len(entry) == 168 + len(entry_name), len(entry)

    # IDX block
    idx = bytearray()
    idx += b"IDX\x00"
    idx += struct.pack("<I", len(gz))              # compressed size
    idx += struct.pack("<I", 92 + len(gz))         # end offset
    idx += struct.pack("<I", 0)
    idx += struct.pack("<I", len(entry))           # tail size
    idx += struct.pack("<I", 0)
    idx += struct.pack("<I", 0)

    # VFS header (64 bytes)
    head = bytearray(b"VFS\x00")
    head += struct.pack("<I", 1)                   # version
    head += struct.pack("<I", 64)                  # data offset
    head += b"\x00" * 52
    assert len(head) == 64

    return bytes(head) + bytes(idx) + gz + bytes(entry)


# ---------------------------------------------------------------------------
# Audio: ffmpeg
# ---------------------------------------------------------------------------

_FFMPEG = None


def ffmpeg_exe():
    global _FFMPEG
    if _FFMPEG is None:
        try:
            import imageio_ffmpeg
            _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            _FFMPEG = shutil.which("ffmpeg")
        if not _FFMPEG:
            raise RuntimeError("ffmpeg nahi mila. `pip install imageio-ffmpeg` karo.")
    return _FFMPEG


def ffmpeg_run(args):
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[:800])
    return p.stdout


def probe_wav(path):
    """wav header se (rate, channels, frames) nikalta hai."""
    with open(path, "rb") as f:
        d = f.read(200000)
    if d[:4] != b"RIFF" or d[8:12] != b"WAVE":
        raise ValueError(f"{path}: WAV nahi hai")
    i = 12
    fmt = None
    while i + 8 <= len(d):
        cid = d[i:i + 4]
        size = struct.unpack("<I", d[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", d[i + 8:i + 24])
            break
        i += 8 + size + (size & 1)
    if not fmt:
        raise ValueError(f"{path}: fmt chunk nahi mila")
    _tag, ch, rate, _br, _ba, bits = fmt
    # frames ke liye poora file scan
    with open(path, "rb") as f:
        raw = f.read()
    i = 12
    frames = 0
    while i + 8 <= len(raw):
        cid = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        if cid == b"data":
            frames = size // max(1, (ch * bits // 8))
            break
        i += 8 + size + (size & 1)
    return rate, ch, frames


def prepare_wav(src_path, out_path):
    """Koi bhi audio (wav/mp3/m4a/ogg) -> 44.1kHz stereo 16-bit WAV."""
    ffmpeg_run(["-y", "-i", src_path, "-map", "a:0",
                "-acodec", "pcm_s16le", "-ar", str(SAMPLE_RATE),
                "-ac", str(CHANNELS), out_path])
    return out_path


def encode_m4a(wav_path, out_path):
    """WebGL payload: MP4 container, AAC-LC, 44.1kHz stereo, ~98 kbps."""
    args = ["-y", "-i", wav_path,
            "-map", "a:0",
            "-c:a", "aac", "-b:a", "98k",
            "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
            "-brand", "mp42", "-movflags", "+faststart",
            out_path]
    ffmpeg_run(args)
    with open(out_path, "rb") as f:
        return f.read()


def normalize_ftyp(mp4):
    """ffmpeg ke ftyp box ko reference jaisa chhota box bana deta hai."""
    if len(mp4) < 12 or mp4[4:8] != b"ftyp":
        return mp4
    size = struct.unpack(">I", mp4[:4])[0]
    if size < 8 or size > len(mp4):
        return mp4
    ref_box = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp41isom"
    return ref_box + mp4[size:]


def encode_pcm16(wav_path, out_path):
    """NotWebGL payload ke liye raw PCM16 (44.1kHz stereo)."""
    args = ["-y", "-i", wav_path,
            "-map", "a:0",
            "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
            "-f", "s16le", out_path]
    ffmpeg_run(args)
    with open(out_path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Descriptor (.bytes)
# ---------------------------------------------------------------------------

def make_registry(reg_id, namespace, package_suffix, version_md5):
    """Template registry blob me identifiers replace karke naya gzip blob."""
    if not os.path.isfile(TEMPLATE_PATH):
        raise FileNotFoundError(f"template not found: {TEMPLATE_PATH}")
    with open(TEMPLATE_PATH, "rb") as f:
        blob = f.read()
    repl = {"reg_id": reg_id, "namespace": namespace,
            "package_suffix": package_suffix, "version_md5": version_md5}
    for old, key in TEMPLATE_REPLACEMENTS:
        new = repl[key]
        if len(old) != len(new):
            raise ValueError(f"length mismatch {key}: {len(old)} != {len(new)}")
        blob = blob.replace(old.encode(), new.encode())
    return gzip.compress(blob, compresslevel=6, mtime=0)


def build_descriptor(asset_id, name, sound_file, webgl_bytes, notwebgl_bytes,
                     base_url, author, code, namespace, package_suffix,
                     child_uuid, reg_id, version_md5, duration):
    sha_web = base64.b64encode(hashlib.sha1(webgl_bytes).digest()).decode()
    sha_nw = base64.b64encode(hashlib.sha1(notwebgl_bytes).digest()).decode()
    url_web = base_url.rstrip("/") + f"/{asset_id}/WebGL"
    url_nw = base_url.rstrip("/") + f"/{asset_id}/NotWebGL"
    package_name = f"{namespace}.{package_suffix}"

    def file_info(sub_id, sha, size, url, mask):
        return (fbytes(1, sub_id.encode()) + fbytes(2, sha.encode())
                + fvar(3, size) + fbytes(4, url.encode()) + fvar(5, mask))

    # manifest = repeated package; package = { 1: name, 2: file (repeated), 3: 0 }
    package = (fbytes(1, package_name.encode())
               + fbytes(2, file_info("WebGL", sha_web, len(webgl_bytes), url_web, 4))
               + fbytes(2, file_info("NotWebGL", sha_nw, len(notwebgl_bytes), url_nw, 3))
               + fvar(3, 0))
    manifest = fbytes(1, package)

    registry = make_registry(reg_id, namespace, package_suffix, version_md5)

    inner = (fvar(1, 14) + fbytes(2, registry) + fvar(3, 115)
             + fbytes(4, manifest) + fvar(5, 1))

    meta = {
        "W!9p4B#3RvTc": "ref",
        "AppVersion": APP_VERSION,
        "ContentVersion": {"FF": 5001},
        "Name": name,
        "UUID": namespace,
        "Children": [{
            "Name": os.path.basename(sound_file),
            "UUID": child_uuid,
            "Type": "sound",
            "PackageUUID": package_name,
            "RelyOns": [f"{namespace}.{child_uuid}"],
            "Info": {"timelength": round(duration, 7)},
        }],
        "ResPackages": [{
            "Name": package_name,
            "UUID": package_name,
            "UseVersionMD5": version_md5,
            "WhoRequire": 0,
            "FileList": [
                {"SubFileID": "WebGL", "SHA1": sha_web, "FileSize": len(webgl_bytes),
                 "URL": url_web, "PlatformRequireMask": 4},
                {"SubFileID": "NotWebGL", "SHA1": sha_nw, "FileSize": len(notwebgl_bytes),
                 "URL": url_nw, "PlatformRequireMask": 3},
            ],
        }],
        "StoreInfo": {
            "store_env": "https://assetstore.sea.garena.com",
            "asset_id": asset_id,
            "ob_version": 1,
            "Title": name,
            "Desc": "",
            "Author": author,
            "fe_version": APP_VERSION,
            "Thumbnails": [],
            "fe_namespace": namespace,
            "Tags": [],
            "CategoryL1": 0,
            "CategoryL2": 0,
            "ResourceType": 2,
            "Thumbnails_CL": [],
            "Category_CL_Main": 10003,
            "Category_CL": 201,
            "resource_code": code,
        },
    }
    json_bytes = json.dumps(meta, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    return (fbytes(1, inner) + fbytes(2, json_bytes)
            + fbytes(3, b"") + fbytes(4, b'{"Prefabs":[]}'))


# ---------------------------------------------------------------------------
# NRBF index writer
# ---------------------------------------------------------------------------

def _lps(s):
    b = s.encode("utf-8")
    n = len(b)
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n:
            out.append(x | 0x80)
        else:
            out.append(x)
            break
    return bytes(out) + b


def _i32(v):
    return struct.pack("<i", v)


def _type_info(members):
    out = bytearray()
    for _, bt, _ in members:
        out.append(bt)
    for _, bt, add in members:
        if bt == 0:
            out.append(add)
        elif bt == 3:
            out += _lps(add)
        elif bt == 4:
            out += _lps(add[0]) + _i32(add[1])
    return bytes(out)


def _class_record(obj_id, type_name, members, lib_id, values):
    out = bytearray(b"\x05") + _i32(obj_id) + _lps(type_name) + _i32(len(members))
    for n, _, _ in members:
        out += _lps(n)
    out += _type_info(members)
    out += _i32(lib_id) + values
    return bytes(out)


def _sysclass_record(obj_id, type_name, members, values):
    out = bytearray(b"\x04") + _i32(obj_id) + _lps(type_name) + _i32(len(members))
    for n, _, _ in members:
        out += _lps(n)
    out += _type_info(members)
    out += values
    return bytes(out)


def _string_record(obj_id, s):
    return b"\x06" + _i32(obj_id) + _lps(s)


def build_index(entries):
    out = bytearray()
    out += b"\x00" + _i32(1) + _i32(-1) + _i32(1) + _i32(0)
    out += b"\x0c" + _i32(2) + _lps(LIB_NAME)

    arr = bytearray(b"\x10" + _i32(4) + _i32(len(entries)))
    sid = 5 + len(entries)
    for idx, e in enumerate(entries):
        vals = bytearray()
        vals += _i32(int(e["ResourceId"])) + _i32(int(e.get("Version", 1)))
        for key in ("ResourceCode", "ResourceName", "ResourceDesc"):
            vals += _string_record(sid, str(e[key]))
            sid += 1
        vals += _i32(int(e.get("ResourceType", 2)))
        vals += _i32(int(e.get("MainCategory", 10003)))
        vals += _i32(int(e.get("SubCategory", 201)))
        vals += _i32(int(e.get("Recreation", 0)))
        if idx == 0:
            arr += _class_record(5, ENTRY_TYPE, [
                ("ResourceId", 0, 8), ("Version", 0, 8),
                ("ResourceCode", 1, None), ("ResourceName", 1, None),
                ("ResourceDesc", 1, None), ("ResourceType", 0, 8),
                ("MainCategory", 0, 8), ("SubCategory", 0, 8),
                ("Recreation", 0, 8)], 2, bytes(vals))
        else:
            arr += b"\x01" + _i32(5 + idx) + _i32(5) + bytes(vals)

    list_vals = bytes(arr) + _i32(len(entries)) + _i32(len(entries))
    list_rec = _sysclass_record(3, LIST_TYPE, [
        ("_items", 4, ("COW.Gameplay.UGC.UGCResourceIndexEntry[]", 2)),
        ("_size", 0, 8), ("_version", 0, 8)], list_vals)
    out += _class_record(1, "COW.Gameplay.UGC.UGCResourceIndexData",
                         [("Entries", 3, LIST_TYPE)], 2, list_rec)
    out += b"\x0b"
    return bytes(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Craftland sound pack builder")
    ap.add_argument("--sounds", required=True, help=".wav files ka folder")
    ap.add_argument("--repo", required=True, help="USER/REPO")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--path", default="", help="repo ke andar sub-folder (optional)")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--author", default="Unknown")
    ap.add_argument("--code", default="MYCODE")
    ap.add_argument("--start-id", type=int, default=679001)
    ap.add_argument("--uid", default="", help="in-game UID (UID folder ka naam)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    base = f"https://raw.githubusercontent.com/{args.repo}/refs/heads/{args.branch}/"
    if args.path:
        base += args.path.strip("/") + "/"

    exts = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac")
    sounds = sorted(f for f in os.listdir(args.sounds) if f.lower().endswith(exts))
    if not sounds:
        print("[!] koi audio file nahi mili:", args.sounds)
        return 1

    store_dir = os.path.join(args.out, "Store")
    uid_dir = os.path.join(args.out, "UID")
    upload_dir = os.path.join(args.out, "upload")
    for d in (store_dir, uid_dir, upload_dir):
        os.makedirs(d, exist_ok=True)

    entries = []
    for i, fname in enumerate(sounds):
        asset_id = args.start_id + i
        name = os.path.splitext(fname)[0]
        path = os.path.join(args.sounds, fname)
        print(f"[{i+1}/{len(sounds)}] {fname} -> {asset_id}")

        tmp = os.path.join(args.out, "_tmp")
        os.makedirs(tmp, exist_ok=True)
        norm = os.path.join(tmp, f"{asset_id}_norm.wav")
        prepare_wav(path, norm)
        rate, ch, frames = probe_wav(norm)
        duration = frames / rate if rate else 0.0

        m4a = os.path.join(tmp, f"{asset_id}.m4a")
        pcm = os.path.join(tmp, f"{asset_id}.pcm")
        encode_m4a(norm, m4a)
        with open(m4a, "rb") as f:
            webgl_audio = normalize_ftyp(f.read())
        encode_pcm16(norm, pcm)
        with open(pcm, "rb") as f:
            pcm_data = f.read()

        fsb = build_fsb5_pcm16(pcm_data, CHANNELS, SAMPLE_RATE, frames)
        src_name = "Assets\\" + os.path.basename(fname)

        namespace = rand_str(8)
        package_suffix = rand_str(20)
        child_uuid = rand_uuid()
        reg_id = rand_str(9)
        version_md5 = base64.b64encode(hashlib.sha1(webgl_audio + fsb).digest()).decode()
        entry_name = f"{namespace}.{child_uuid}"

        webgl_vfs = build_vfs(build_vernum(name, CHANNELS, SAMPLE_RATE, frames, webgl_audio),
                              entry_name, src_name)
        nw_vfs = build_vfs(build_vernum(name, CHANNELS, SAMPLE_RATE, frames, fsb),
                           entry_name, src_name)

        desc = build_descriptor(asset_id, name, fname, webgl_vfs, nw_vfs, base,
                                args.author, args.code, namespace, package_suffix,
                                child_uuid, reg_id, version_md5, duration)

        with open(os.path.join(store_dir, f"{asset_id}_1.bytes"), "wb") as f:
            f.write(desc)

        for sub, blob in (("WebGL", webgl_vfs), ("NotWebGL", nw_vfs)):
            d = os.path.join(upload_dir, str(asset_id))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, sub), "wb") as f:
                f.write(blob)

        entries.append({
            "ResourceId": asset_id,
            "ResourceCode": args.code,
            "ResourceName": name,
            "ResourceDesc": f"SFX by {args.author}",
        })

    shutil.rmtree(os.path.join(args.out, "_tmp"), ignore_errors=True)

    if args.uid:
        uid_path = os.path.join(args.out, str(args.uid))
        if os.path.isdir(uid_path):
            shutil.rmtree(uid_path)
        os.rename(uid_dir, uid_path)
        uid_dir = uid_path

    with open(os.path.join(uid_dir, "ResourceIndex.bytes"), "wb") as f:
        f.write(build_index(entries))

    print(f"\n[OK] {len(entries)} sounds")
    print(f"     Store   : {store_dir}")
    print(f"     Index   : {uid_dir}/ResourceIndex.bytes")
    print(f"     Upload  : {upload_dir}  (GitHub: {args.repo}/{args.path})")
    print(f"     Base URL: {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

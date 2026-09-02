#!/usr/bin/env python3
"""提取脚本所在目录内所有 .eb3 的 AC-3 核心。

用法：
    python extract_eb3_core.py
    python extract_eb3_core.py --force   # 原子覆盖已有的同名 .ac3

脚本只使用 Python 标准库，不扫描子目录，也不修改源 .eb3 文件。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path


SYNCWORD = b"\x0b\x77"

# AC-3 syncframe size table, in 16-bit words. Columns are 48/44.1/32 kHz.
AC3_FRAME_SIZE_WORDS = (
    (64, 69, 96), (64, 70, 96), (80, 87, 120), (80, 88, 120),
    (96, 104, 144), (96, 105, 144), (112, 121, 168), (112, 122, 168),
    (128, 139, 192), (128, 140, 192), (160, 174, 240), (160, 175, 240),
    (192, 208, 288), (192, 209, 288), (224, 243, 336), (224, 244, 336),
    (256, 278, 384), (256, 279, 384), (320, 348, 480), (320, 349, 480),
    (384, 417, 576), (384, 418, 576), (448, 487, 672), (448, 488, 672),
    (512, 557, 768), (512, 558, 768), (640, 696, 960), (640, 697, 960),
    (768, 835, 1152), (768, 836, 1152), (896, 975, 1344), (896, 976, 1344),
    (1024, 1114, 1536), (1024, 1115, 1536),
    (1152, 1253, 1728), (1152, 1254, 1728),
    (1280, 1393, 1920), (1280, 1394, 1920),
)


class StreamError(ValueError):
    """输入不是受支持的连续 AC-3/E-AC-3 syncframe 流。"""


def frame_kind_and_size(header: bytes, offset: int) -> tuple[str, int]:
    if len(header) < 8:
        raise StreamError(f"偏移 {offset} 处的帧头不完整")
    if header[:2] != SYNCWORD:
        raise StreamError(f"偏移 {offset} 未找到 syncword 0x0B77")

    bsid = header[5] >> 3
    if bsid <= 10:
        fscod = header[4] >> 6
        frmsizecod = header[4] & 0x3F
        if fscod > 2 or frmsizecod >= len(AC3_FRAME_SIZE_WORDS):
            raise StreamError(f"偏移 {offset} 的 AC-3 帧头无效")
        return "AC-3", AC3_FRAME_SIZE_WORDS[frmsizecod][fscod] * 2

    # E-AC-3: frmsiz is the low 11 bits following syncword, in 16-bit words - 1.
    frame_size = ((int.from_bytes(header[2:4], "big") & 0x07FF) + 1) * 2
    if frame_size < 8:
        raise StreamError(f"偏移 {offset} 的 E-AC-3 帧长无效")
    return "E-AC-3", frame_size


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_core(source: Path, target: Path, force: bool) -> tuple[int, int, str]:
    ac3_frames = 0
    eac3_frames = 0
    core_digest = hashlib.sha256()
    temp_path: Path | None = None

    try:
        with source.open("rb") as src, tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as dst:
            temp_path = Path(dst.name)
            while True:
                offset = src.tell()
                header = src.read(8)
                if not header:
                    break

                kind, frame_size = frame_kind_and_size(header, offset)
                payload = header + src.read(frame_size - len(header))
                if len(payload) != frame_size:
                    raise StreamError(
                        f"偏移 {offset} 的 {kind} 帧被截断："
                        f"需要 {frame_size} 字节，实际 {len(payload)} 字节"
                    )

                if kind == "AC-3":
                    dst.write(payload)
                    core_digest.update(payload)
                    ac3_frames += 1
                else:
                    eac3_frames += 1

            if ac3_frames == 0:
                raise StreamError("流中没有可提取的 AC-3 核心帧")

            dst.flush()
            os.fsync(dst.fileno())

        digest = core_digest.hexdigest()
        if target.exists() and not force:
            if target.stat().st_size == temp_path.stat().st_size and file_sha256(target) == digest:
                temp_path.unlink()
                return ac3_frames, eac3_frames, "unchanged"
            raise FileExistsError(
                f"{target.name} 已存在且内容不同；如需原子覆盖，请使用 --force"
            )

        os.replace(temp_path, target)
        temp_path = None
        return ac3_frames, eac3_frames, "written"
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="提取脚本所在目录内所有 .eb3 的 AC-3 核心并保存为同名 .ac3"
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="原子覆盖已存在且内容不同的同名 .ac3",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = Path(__file__).resolve().parent
    sources = sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".eb3"),
        key=lambda path: path.name.casefold(),
    )

    print(f"扫描目录：{folder}")
    if not sources:
        print("未找到 .eb3 文件。")
        return 0

    failures = 0
    for source in sources:
        target = source.with_suffix(".ac3")
        try:
            ac3_count, eac3_count, status = extract_core(source, target, args.force)
            label = "已写入" if status == "written" else "内容相同，无需改写"
            print(
                f"[成功] {source.name} -> {target.name}：{label}；"
                f"AC-3 {ac3_count} 帧，跳过 E-AC-3 {eac3_count} 帧"
            )
        except (OSError, StreamError) as exc:
            failures += 1
            print(f"[失败] {source.name}：{exc}", file=sys.stderr)

    print(f"完成：成功 {len(sources) - failures}，失败 {failures}。")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
对齐 heribase-coin-h5/src/utils/index.js 的 uploadCdn 流程，上传单个或多个本地文件到 CDN。
# 上传单个文件
python -m cdn_upload 04-StructuredOutput/assets/pydantic-workflow.png

# 上传整个目录（递归）
python -m cdn_upload ./images --recursive

# 指定业务参数
python -m cdn_upload ./a.png --biz appraiser --scene coin
"""

from __future__ import annotations

import mimetypes
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

DEFAULT_API_HOST = os.getenv("CDN_API_HOST", "https://api.heribase.com")
DEFAULT_API_PATH = os.getenv("CDN_API_PATH", "/app/v1")
PRESIGN_ENDPOINT = "/file-pre-signed-req"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg",
                  ".webp", ".gif", ".bmp", ".tif", ".tiff"}


@dataclass
class UploadResult:
    """单文件上传结果。"""

    local_path: Path
    url: str
    pre_url: str
    width: int
    height: int
    suffix: str


def upload_file(
    file_path: str | Path,
    *,
    biz: str = "appraiser",
    scene: str = "coin",
    file_type: int = 1,
    api_host: str | None = None,
    api_path: str | None = None,
    token: str | None = None,
    uuid: str | None = None,
    timeout: int = 60,
) -> UploadResult:
    """上传单个本地图片到 CDN。

  流程与前端 uploadCdn 一致：
  1. POST /file-pre-signed-req 获取预签名 URL
  2. PUT 文件到 S3 预签名地址
  3. 返回 visitUrl

    Args:
        file_path: 本地图片路径。
        biz: 业务类型，如 identify / appraiser / favorite。
        scene: 场景值，如 coin / note / d。
        file_type: 1 图片，2 视频，3 音频。
        api_host: API 域名，默认读取 CDN_API_HOST。
        api_path: API 路径前缀，默认 /app/v1。
        token: 可选登录 token，对应请求头 ut。
        uuid: 可选设备 uuid，对应请求头 uuid。
        timeout: 请求超时秒数。
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")

    width, height = _get_image_size(path)
    suffix = _resolve_suffix(path)
    content_type = mimetypes.guess_type(
        path.name)[0] or "application/octet-stream"
    file_bytes = path.read_bytes()

    presign = _request_presigned_url(
        suffix=suffix,
        width=width,
        height=height,
        biz=biz,
        scene=scene,
        file_type=file_type,
        api_host=api_host or DEFAULT_API_HOST,
        api_path=api_path or DEFAULT_API_PATH,
        token=token or os.getenv("CDN_UPLOAD_UT"),
        uuid=uuid or os.getenv("CDN_UPLOAD_UUID"),
        timeout=timeout,
    )

    _put_file(
        presign["preUrl"],
        file_bytes,
        content_type=content_type,
        timeout=timeout,
    )

    return UploadResult(
        local_path=path,
        url=presign["visitUrl"],
        pre_url=presign["preUrl"],
        width=width,
        height=height,
        suffix=suffix,
    )


def upload_files(
    file_paths: list[str | Path],
    **kwargs,
) -> list[UploadResult]:
    """批量上传多个本地文件。"""
    return [upload_file(path, **kwargs) for path in file_paths]


def upload_directory(
    directory: str | Path,
    *,
    recursive: bool = True,
    **kwargs,
) -> list[UploadResult]:
    """上传目录下的所有图片文件。"""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"目录不存在: {root}")

    if recursive:
        candidates = [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
    else:
        candidates = [
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]

    if not candidates:
        raise ValueError(f"目录中没有可上传的图片: {root}")

    return upload_files(sorted(candidates), **kwargs)


def _get_image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:
        return _get_image_size_stdlib(path)


def _get_image_size_stdlib(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)

    if len(data) >= 2 and data.startswith(b"\xff\xd8"):
        return _parse_jpeg_size(data)

    if len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
        width, height = struct.unpack("<HH", data[6:10])
        return int(width), int(height)

    return 100, 100


def _parse_jpeg_size(data: bytes) -> tuple[int, int]:
    index = 2
    while index < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 1 >= len(data):
            break
        segment_length = struct.unpack(">H", data[index: index + 2])[0]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 5 < len(data):
                height, width = struct.unpack(
                    ">HH", data[index + 3: index + 7])
                return int(width), int(height)
            break
        index += segment_length
    return 100, 100


def _resolve_suffix(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "jpg":
        return "jpeg"
    if suffix:
        return suffix
    return "png"


def _request_presigned_url(
    *,
    suffix: str,
    width: int,
    height: int,
    biz: str,
    scene: str,
    file_type: int,
    api_host: str,
    api_path: str,
    token: str | None,
    uuid: str | None,
    timeout: int,
) -> dict[str, str]:
    url = f"{api_host.rstrip('/')}{api_path}{PRESIGN_ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["ut"] = token
    if uuid:
        headers["uuid"] = uuid

    payload = {
        "type": file_type,
        "suffix": suffix,
        "biz": biz,
        "scene": scene,
        "width": width,
        "height": height,
    }

    response = requests.post(
        url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    body = response.json()

    if body.get("code") != 0:
        raise RuntimeError(f"获取预签名 URL 失败: {body.get('msg') or body}")

    data = body.get("data") or {}
    pre_url = data.get("preUrl")
    visit_url = data.get("visitUrl")
    if not pre_url or not visit_url:
        raise RuntimeError(f"预签名响应缺少 URL 字段: {body}")

    return {"preUrl": pre_url, "visitUrl": visit_url}


def _put_file(
    pre_url: str,
    file_bytes: bytes,
    *,
    content_type: str,
    timeout: int,
) -> None:
    response = requests.put(
        pre_url,
        data=file_bytes,
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(file_bytes)),
        },
        timeout=timeout,
    )
    response.raise_for_status()

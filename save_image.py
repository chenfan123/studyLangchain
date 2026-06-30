"""根据图片链接下载并保存到项目根目录。"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parent


def save_image_from_url(
    url: str,
    filename: str | None = None,
    save_dir: str | Path | None = None,
) -> Path:
    """根据图片链接下载图片并保存到指定目录（默认为项目根目录）。

    Args:
        url: 图片链接。
        filename: 保存的文件名；不传则从 URL 自动推断。
        save_dir: 保存目录；默认为本项目根目录。

    Returns:
        保存后的图片绝对路径。

    Raises:
        requests.HTTPError: 下载失败时抛出。
        ValueError: 无法确定文件名时抛出。
    """
    target_dir = Path(save_dir) if save_dir is not None else PROJECT_ROOT
    target_dir.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    resolved_name = filename or _guess_filename(
        url, response.headers.get("Content-Type"))
    if not resolved_name:
        raise ValueError("无法从 URL 或响应头推断文件名，请手动传入 filename")

    output_path = target_dir / resolved_name
    output_path.write_bytes(response.content)
    return output_path.resolve()


def _guess_filename(url: str, content_type: str | None) -> str | None:
    path_name = Path(unquote(urlparse(url).path)).name
    if path_name and "." in path_name:
        return path_name

    if content_type:
        extension = mimetypes.guess_extension(
            content_type.split(";", 1)[0].strip())
        if extension:
            return f"image{extension}"

    return None


if __name__ == "__main__":
    demo_url = (
        "https://cdn.heritcoin.com/sky/official/d/image/20260630/c173245yryw0qrkjsh-W1280H574.png"
    )
    saved_path = save_image_from_url(demo_url, filename="demo-workflow.png")
    print(f"图片已保存: {saved_path}")

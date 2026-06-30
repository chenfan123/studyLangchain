"""命令行上传本地图片或目录到 CDN。"""

from __future__ import annotations

import argparse
from pathlib import Path

from cdn_upload.uploader import upload_directory, upload_file


def main() -> None:
    parser = argparse.ArgumentParser(description="上传本地图片到 CDN")
    parser.add_argument("path", help="图片文件或目录路径")
    parser.add_argument("--biz", default="appraiser", help="业务类型，默认 appraiser")
    parser.add_argument("--scene", default="coin", help="场景值，默认 coin")
    parser.add_argument(
        "--api-host",
        default=None,
        help="API 域名，默认读取环境变量 CDN_API_HOST",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="上传目录时递归扫描子目录",
    )
    args = parser.parse_args()

    target = Path(args.path).expanduser().resolve()
    common_kwargs = {
        "biz": args.biz,
        "scene": args.scene,
        "api_host": args.api_host,
    }

    if target.is_file():
        results = [upload_file(target, **common_kwargs)]
    elif target.is_dir():
        results = upload_directory(target, recursive=args.recursive, **common_kwargs)
    else:
        raise SystemExit(f"路径不存在: {target}")

    for item in results:
        print(f"{item.local_path} -> {item.url}")


if __name__ == "__main__":
    main()

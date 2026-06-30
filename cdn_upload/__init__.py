"""本地图片上传到 HeritCoin / Heribase CDN 的工具包。"""

from cdn_upload.uploader import (
    UploadResult,
    upload_directory,
    upload_file,
    upload_files,
)

__all__ = [
    "UploadResult",
    "upload_file",
    "upload_files",
    "upload_directory",
]

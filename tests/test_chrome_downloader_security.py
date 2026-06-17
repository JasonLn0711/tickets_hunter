from io import BytesIO
import zipfile

import pytest

import chrome_downloader


def make_zip(member_name, content=b"ok"):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(member_name, content)
    buffer.seek(0)
    return buffer


def test_safe_extract_zip_extracts_safe_members(tmp_path):
    archive = make_zip("chrome-linux64/chrome")

    with zipfile.ZipFile(archive, "r") as zip_file:
        chrome_downloader.safe_extract_zip(zip_file, str(tmp_path))

    assert (tmp_path / "chrome-linux64" / "chrome").read_bytes() == b"ok"


def test_safe_extract_zip_rejects_parent_traversal(tmp_path):
    archive = make_zip("../evil.exe")

    with zipfile.ZipFile(archive, "r") as zip_file:
        with pytest.raises(ValueError):
            chrome_downloader.safe_extract_zip(zip_file, str(tmp_path))


def test_no_ssl_mode_is_rejected():
    with pytest.raises(ValueError):
        chrome_downloader.get_chrome_download_info(no_ssl=True)

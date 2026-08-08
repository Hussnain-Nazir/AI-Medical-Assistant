import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.api.routes_upload import _save_upload_with_size_limit
from app.core.exceptions import FileTooLargeError


def _make_upload_file(content: bytes, filename: str = "test.pdf") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


def test_save_upload_within_limit_succeeds(tmp_path):
    destination = tmp_path / "saved.pdf"
    upload = _make_upload_file(b"%PDF-1.4 small file content")

    _save_upload_with_size_limit(upload, destination, max_size_bytes=1024)

    assert destination.exists()
    assert destination.read_bytes() == b"%PDF-1.4 small file content"


def test_save_upload_exceeding_limit_raises_and_cleans_up(tmp_path):
    destination = tmp_path / "too_big.pdf"
    upload = _make_upload_file(b"x" * 5000)

    with pytest.raises(FileTooLargeError):
        _save_upload_with_size_limit(upload, destination, max_size_bytes=1024)

    # The partially-written file must not be left behind.
    assert not destination.exists()

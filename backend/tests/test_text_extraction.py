from pathlib import Path

import pytest

from src.core.exceptions import ValidationException
from src.ingestion.text_extraction import document_text_extractor


def test_text_extractor_reads_txt_segments(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("Điều 1. Nội dung\n\n  1. Khoản một  ", encoding="utf-8")

    segments = document_text_extractor.extract_segments("txt", source)

    assert segments == ["Điều 1. Nội dung", "1. Khoản một"]
    assert document_text_extractor.extract_text("txt", source) == "Điều 1. Nội dung\n1. Khoản một"


def test_text_extractor_rejects_unsupported_type(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"data")

    with pytest.raises(ValidationException):
        document_text_extractor.extract_segments("bin", source)

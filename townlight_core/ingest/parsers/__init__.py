from pathlib import Path
from townlight_core.ingest.parsers.base import BaseParser, ParseResult
from townlight_core.ingest.parsers.csv_parser import CsvParser
from townlight_core.ingest.parsers.docx import DocxParser
from townlight_core.ingest.parsers.email import EmailParser
from townlight_core.ingest.parsers.html import HtmlParser
from townlight_core.ingest.parsers.pdf import PdfParser
from townlight_core.ingest.parsers.text import TextParser
from townlight_core.ingest.parsers.xlsx import XlsxParser

_PARSERS: list[BaseParser] = [PdfParser(), DocxParser(), XlsxParser(), CsvParser(), EmailParser(), HtmlParser(), TextParser()]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}

def detect_parser(file_path: Path) -> BaseParser | None:
    for parser in _PARSERS:
        if parser.can_parse(file_path):
            return parser
    return None

def is_image_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in IMAGE_EXTENSIONS

__all__ = ["detect_parser", "is_image_file", "ParseResult", "BaseParser"]

"""
OCR module for document text extraction.

Provides unified interface for multiple OCR engines (Tesseract, EasyOCR).
"""

from .text_extractor import TextExtractor, OCRResult
from .tesseract_processor import TesseractProcessor
from .easyocr_processor import EasyOCRProcessor

__all__ = [
    "TextExtractor",
    "OCRResult",
    "TesseractProcessor",
    "EasyOCRProcessor",
]


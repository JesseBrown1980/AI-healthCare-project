"""
Tesseract OCR processor for printed text extraction.

Tesseract is excellent for printed documents, forms, and structured text.
"""

import logging
import asyncio
from typing import Optional
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .text_extractor import OCRResult

logger = logging.getLogger(__name__)


class TesseractProcessor:
    """Tesseract OCR processor for printed text."""
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize Tesseract processor.
        
        Args:
            tesseract_cmd: Path to tesseract executable (if not in PATH)
        """
        if not TESSERACT_AVAILABLE:
            raise ImportError(
                "Tesseract dependencies not installed. "
                "Install with: pip install pytesseract Pillow"
            )
        
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        logger.info("Tesseract processor initialized")
    
    async def extract_text(
        self,
        image_path: str,
        language: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from image using Tesseract OCR.
        
        Args:
            image_path: Path to image file
            language: Language code (e.g., 'eng', 'spa'). Defaults to 'eng'
        
        Returns:
            OCRResult with extracted text and confidence
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._extract_text_sync,
            image_path,
            language or "eng",
        )
        return result
    
    def _extract_text_sync(
        self,
        image_path: str,
        language: str,
    ) -> OCRResult:
        """Synchronous text extraction (runs in thread pool)."""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT,
            )
            
            # Combine all text
            text_parts = []
            confidences = []
            
            for i, word in enumerate(data["text"]):
                if word.strip():
                    text_parts.append(word)
                    conf = data["conf"][i]
                    if conf > 0:  # Ignore -1 (invalid confidence)
                        confidences.append(conf)
            
            text = " ".join(text_parts)
            
            # Calculate average confidence
            avg_confidence = (
                sum(confidences) / len(confidences) / 100.0
                if confidences
                else 0.0
            )
            
            return OCRResult(
                text=text,
                confidence=avg_confidence,
                engine="tesseract",
                language=language,
                metadata={
                    "word_count": len(text_parts),
                    "confidence_scores": confidences[:10],  # Sample
                },
            )
        
        except Exception as e:
            logger.error("Tesseract OCR extraction failed: %s", str(e))
            raise


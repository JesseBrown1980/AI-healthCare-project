"""
EasyOCR processor for handwritten and printed text extraction.

EasyOCR excels at handwritten text, multi-language support, and complex layouts.
"""

import logging
import asyncio
from typing import Optional, List
from pathlib import Path

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

from .text_extractor import OCRResult

logger = logging.getLogger(__name__)


class EasyOCRProcessor:
    """EasyOCR processor for handwritten and printed text."""
    
    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        """
        Initialize EasyOCR processor.
        
        Args:
            languages: List of language codes (e.g., ['en', 'es']). Defaults to ['en']
            gpu: Use GPU acceleration if available
        """
        if not EASYOCR_AVAILABLE:
            raise ImportError(
                "EasyOCR not installed. "
                "Install with: pip install easyocr"
            )
        
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader = None  # Lazy initialization
        
        logger.info("EasyOCR processor initialized (languages: %s)", self.languages)
    
    def _get_reader(self):
        """Get or create EasyOCR reader (lazy initialization)."""
        if self._reader is None:
            logger.info("Initializing EasyOCR reader (this may take a moment)...")
            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
            )
            logger.info("EasyOCR reader ready")
        return self._reader
    
    async def extract_text(
        self,
        image_path: str,
        language: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from image using EasyOCR.
        
        Args:
            image_path: Path to image file
            language: Language code (ignored, uses initialized languages)
        
        Returns:
            OCRResult with extracted text and confidence
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._extract_text_sync,
            image_path,
        )
        return result
    
    def _extract_text_sync(self, image_path: str) -> OCRResult:
        """Synchronous text extraction (runs in thread pool)."""
        try:
            reader = self._get_reader()
            
            # Extract text
            results = reader.readtext(image_path)
            
            # Combine all text and calculate average confidence
            text_parts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if text.strip():
                    text_parts.append(text)
                    confidences.append(confidence)
            
            text = " ".join(text_parts)
            
            avg_confidence = (
                sum(confidences) / len(confidences)
                if confidences
                else 0.0
            )
            
            return OCRResult(
                text=text,
                confidence=avg_confidence,
                engine="easyocr",
                language=",".join(self.languages),
                metadata={
                    "word_count": len(text_parts),
                    "detection_count": len(results),
                    "confidence_scores": confidences[:10],  # Sample
                },
            )
        
        except Exception as e:
            logger.error("EasyOCR extraction failed: %s", str(e))
            raise


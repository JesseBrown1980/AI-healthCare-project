"""
Unified text extraction interface for OCR operations.

Provides a common interface for multiple OCR engines with fallback support.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from OCR text extraction."""
    
    text: str
    confidence: float
    engine: str
    language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TextExtractor:
    """
    Unified OCR text extractor with multiple engine support.
    
    Supports Tesseract (printed text) and EasyOCR (handwritten + printed).
    Automatically falls back to alternative engines if one fails.
    """
    
    def __init__(
        self,
        tesseract_enabled: bool = True,
        easyocr_enabled: bool = True,
        preferred_engine: str = "tesseract",
    ):
        """
        Initialize text extractor.
        
        Args:
            tesseract_enabled: Enable Tesseract OCR
            easyocr_enabled: Enable EasyOCR
            preferred_engine: Preferred engine ("tesseract" or "easyocr")
        """
        self.tesseract_enabled = tesseract_enabled
        self.easyocr_enabled = easyocr_enabled
        self.preferred_engine = preferred_engine
        
        self._tesseract = None
        self._easyocr = None
        
        # Lazy initialization
        if tesseract_enabled:
            try:
                from .tesseract_processor import TesseractProcessor
                self._tesseract = TesseractProcessor()
                logger.info("Tesseract OCR initialized")
            except Exception as e:
                logger.warning("Tesseract OCR not available: %s", str(e))
                self.tesseract_enabled = False
        
        if easyocr_enabled:
            try:
                from .easyocr_processor import EasyOCRProcessor
                self._easyocr = EasyOCRProcessor()
                logger.info("EasyOCR initialized")
            except Exception as e:
                logger.warning("EasyOCR not available: %s", str(e))
                self.easyocr_enabled = False
    
    async def extract_text(
        self,
        image_path: str,
        language: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            language: Language code (e.g., 'en', 'es')
            engine: Specific engine to use ('tesseract' or 'easyocr'), or None for auto
        
        Returns:
            OCRResult with extracted text and confidence
        
        Raises:
            ValueError: If no OCR engines are available
            FileNotFoundError: If image file doesn't exist
        """
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Determine which engine to use
        if engine:
            if engine == "tesseract" and not self.tesseract_enabled:
                raise ValueError("Tesseract OCR is not enabled")
            if engine == "easyocr" and not self.easyocr_enabled:
                raise ValueError("EasyOCR is not enabled")
        else:
            engine = self.preferred_engine
        
        # Try preferred engine first
        result = None
        errors = []
        
        if engine == "tesseract" and self.tesseract_enabled and self._tesseract:
            try:
                result = await self._tesseract.extract_text(image_path, language)
                logger.info("Tesseract OCR extraction successful")
            except Exception as e:
                errors.append(f"Tesseract: {str(e)}")
                logger.warning("Tesseract OCR failed: %s", str(e))
        
        if result is None and engine == "easyocr" and self.easyocr_enabled and self._easyocr:
            try:
                result = await self._easyocr.extract_text(image_path, language)
                logger.info("EasyOCR extraction successful")
            except Exception as e:
                errors.append(f"EasyOCR: {str(e)}")
                logger.warning("EasyOCR failed: %s", str(e))
        
        # Fallback to alternative engine
        if result is None:
            if engine == "tesseract" and self.easyocr_enabled and self._easyocr:
                try:
                    result = await self._easyocr.extract_text(image_path, language)
                    logger.info("Fallback to EasyOCR successful")
                except Exception as e:
                    errors.append(f"EasyOCR fallback: {str(e)}")
            
            elif engine == "easyocr" and self.tesseract_enabled and self._tesseract:
                try:
                    result = await self._tesseract.extract_text(image_path, language)
                    logger.info("Fallback to Tesseract successful")
                except Exception as e:
                    errors.append(f"Tesseract fallback: {str(e)}")
        
        if result is None:
            error_msg = "All OCR engines failed. " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        return result
    
    def is_available(self) -> bool:
        """Check if any OCR engine is available."""
        return self.tesseract_enabled or self.easyocr_enabled


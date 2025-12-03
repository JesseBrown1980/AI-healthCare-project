"""
Tests for OCR text extraction functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from backend.ocr.text_extractor import TextExtractor, OCRResult
from backend.ocr.tesseract_processor import TesseractProcessor
from backend.ocr.easyocr_processor import EasyOCRProcessor


@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image file for testing."""
    # Create a dummy image file
    image_path = tmp_path / "test_image.png"
    image_path.write_bytes(b"fake image data")
    return str(image_path)


@pytest.fixture
def text_extractor():
    """Create TextExtractor instance."""
    return TextExtractor(
        tesseract_enabled=True,
        easyocr_enabled=True,
        preferred_engine="tesseract",
    )


def test_text_extractor_initialization():
    """Test TextExtractor initialization."""
    extractor = TextExtractor()
    assert extractor.preferred_engine == "tesseract"
    assert extractor.tesseract_enabled is True
    assert extractor.easyocr_enabled is True


def test_text_extractor_initialization_disabled():
    """Test TextExtractor with engines disabled."""
    extractor = TextExtractor(
        tesseract_enabled=False,
        easyocr_enabled=False,
    )
    assert extractor.is_available() is False


@pytest.mark.asyncio
async def test_extract_text_with_tesseract(text_extractor, sample_image_path):
    """Test text extraction using Tesseract."""
    with patch.object(text_extractor, "_tesseract") as mock_tesseract:
        mock_result = OCRResult(
            text="Sample extracted text",
            confidence=0.95,
            engine="tesseract",
            language="eng",
        )
        mock_tesseract.extract_text = AsyncMock(return_value=mock_result)
        text_extractor.tesseract_enabled = True
        
        result = await text_extractor.extract_text(
            sample_image_path,
            language="eng",
            engine="tesseract",
        )
        
        assert result.text == "Sample extracted text"
        assert result.confidence == 0.95
        assert result.engine == "tesseract"
        mock_tesseract.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_extract_text_with_easyocr(text_extractor, sample_image_path):
    """Test text extraction using EasyOCR."""
    with patch.object(text_extractor, "_easyocr") as mock_easyocr:
        mock_result = OCRResult(
            text="EasyOCR extracted text",
            confidence=0.88,
            engine="easyocr",
            language="en",
        )
        mock_easyocr.extract_text = AsyncMock(return_value=mock_result)
        text_extractor.easyocr_enabled = True
        
        result = await text_extractor.extract_text(
            sample_image_path,
            language="en",
            engine="easyocr",
        )
        
        assert result.text == "EasyOCR extracted text"
        assert result.confidence == 0.88
        assert result.engine == "easyocr"
        mock_easyocr.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_extract_text_fallback(text_extractor, sample_image_path):
    """Test fallback to alternative engine when primary fails."""
    with patch.object(text_extractor, "_tesseract") as mock_tesseract, \
         patch.object(text_extractor, "_easyocr") as mock_easyocr:
        
        # Tesseract fails
        mock_tesseract.extract_text = AsyncMock(side_effect=Exception("Tesseract error"))
        
        # EasyOCR succeeds
        mock_result = OCRResult(
            text="Fallback text",
            confidence=0.85,
            engine="easyocr",
        )
        mock_easyocr.extract_text = AsyncMock(return_value=mock_result)
        
        text_extractor.tesseract_enabled = True
        text_extractor.easyocr_enabled = True
        
        result = await text_extractor.extract_text(
            sample_image_path,
            engine="tesseract",
        )
        
        assert result.text == "Fallback text"
        assert result.engine == "easyocr"
        mock_tesseract.extract_text.assert_called_once()
        mock_easyocr.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_extract_text_file_not_found(text_extractor):
    """Test error handling when image file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        await text_extractor.extract_text("/nonexistent/image.png")


@pytest.mark.asyncio
async def test_extract_text_all_engines_fail(text_extractor, sample_image_path):
    """Test error handling when all engines fail."""
    with patch.object(text_extractor, "_tesseract") as mock_tesseract, \
         patch.object(text_extractor, "_easyocr") as mock_easyocr:
        
        mock_tesseract.extract_text = AsyncMock(side_effect=Exception("Tesseract error"))
        mock_easyocr.extract_text = AsyncMock(side_effect=Exception("EasyOCR error"))
        
        text_extractor.tesseract_enabled = True
        text_extractor.easyocr_enabled = True
        
        with pytest.raises(ValueError, match="All OCR engines failed"):
            await text_extractor.extract_text(sample_image_path)


@pytest.mark.asyncio
async def test_extract_text_engine_not_enabled(text_extractor, sample_image_path):
    """Test error when requesting disabled engine."""
    text_extractor.tesseract_enabled = False
    
    with pytest.raises(ValueError, match="Tesseract OCR is not enabled"):
        await text_extractor.extract_text(sample_image_path, engine="tesseract")


def test_is_available():
    """Test availability check."""
    extractor = TextExtractor(tesseract_enabled=True, easyocr_enabled=True)
    assert extractor.is_available() is True
    
    extractor = TextExtractor(tesseract_enabled=False, easyocr_enabled=False)
    assert extractor.is_available() is False

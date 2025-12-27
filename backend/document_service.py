"""
Document service for handling document uploads, OCR processing, and storage.

Orchestrates the workflow: upload -> OCR -> parse -> FHIR -> database.
"""

import logging
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ocr import TextExtractor, OCRResult
from backend.ocr.medical_parser import MedicalParser
from backend.ocr.fhir_mapper import FHIRMapper
from backend.database import get_db_session, DatabaseService
from backend.database.models import Document, OCRExtraction

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document management and OCR processing."""
    
    def __init__(
        self,
        database_service: Optional[DatabaseService] = None,
        upload_dir: Optional[str] = None,
    ):
        """
        Initialize document service.
        
        Args:
            database_service: Database service for persistence
            upload_dir: Directory for storing uploaded files (defaults to ./uploads)
        """
        self.database_service = database_service
        self.upload_dir = Path(upload_dir or "./uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OCR, parser, and FHIR mapper
        self.text_extractor = TextExtractor()
        self.medical_parser = MedicalParser()
        self.fhir_mapper = FHIRMapper()
        
        logger.info("Document service initialized (upload_dir: %s)", self.upload_dir)
    
    async def save_uploaded_file(
        self,
        file: UploadFile,
        patient_id: Optional[str] = None,
        document_type: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save uploaded file and create database record.
        
        Args:
            file: Uploaded file
            patient_id: Patient ID (optional, can link later)
            document_type: Type of document (lab_result, prescription, etc.)
            created_by: User ID who uploaded the file
        
        Returns:
            Document record with file path and metadata
        """
        # Generate unique filename
        file_id = str(uuid4())
        file_ext = Path(file.filename).suffix if file.filename else ""
        filename = f"{file_id}{file_ext}"
        file_path = self.upload_dir / filename
        
        # Save file
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicates
        if self.database_service:
            existing = await self.database_service.get_document_by_hash(file_hash)
            if existing:
                logger.info("Duplicate file detected: %s", file_hash)
                # Get full document to include document_type
                existing_doc = await self.database_service.get_document(existing["id"])
                return {
                    "id": existing["id"],
                    "file_path": existing["file_path"],
                    "file_hash": existing["file_hash"],
                    "document_type": existing_doc.get("document_type") if existing_doc else None,
                    "duplicate": True,
                }
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info("File saved: %s (size: %d bytes)", file_path, len(content))
        
        # Create database record
        document_data = {
            "id": file_id,
            "patient_id": patient_id,
            "document_type": document_type or self._detect_document_type(file.filename),
            "file_path": str(file_path),
            "file_hash": file_hash,
            "uploaded_at": datetime.now(timezone.utc),
            "created_by": created_by,
        }
        
        if self.database_service:
            await self.database_service.save_document(document_data)
        
        return {
            "id": file_id,
            "file_path": str(file_path),
            "file_hash": file_hash,
            "document_type": document_data["document_type"],
            "duplicate": False,
        }
    
    async def process_document_with_ocr(
        self,
        document_id: str,
        engine: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process document with OCR to extract text.
        
        Args:
            document_id: Document ID
            engine: OCR engine to use ('tesseract' or 'easyocr'), or None for auto
            language: Language code for OCR
        
        Returns:
            OCR result with extracted text and confidence
        """
        if not self.database_service:
            raise ValueError("Database service required for OCR processing")
        
        # Get document
        document = await self.database_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        file_path = document["file_path"]
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Convert PDF to image if needed
        image_path = await self._prepare_image(file_path)
        
        # Extract text with OCR
        logger.info("Processing document %s with OCR (engine: %s)", document_id, engine or "auto")
        ocr_result: OCRResult = await self.text_extractor.extract_text(
            image_path,
            language=language,
            engine=engine,
        )
        
        # Save OCR result
        ocr_data = {
            "document_id": document_id,
            "extracted_text": ocr_result.text,
            "confidence": ocr_result.confidence,
            "engine_used": ocr_result.engine,
            "language": ocr_result.language,
            "metadata": ocr_result.metadata,
        }
        
        await self.database_service.save_ocr_extraction(ocr_data)
        
        # Parse medical data from OCR text
        logger.info("Parsing medical data from OCR text...")
        parsed_data = self.medical_parser.parse(ocr_result.text)
        
        # Update document with OCR text and parsed data
        await self.database_service.update_document(
            document_id,
            {
                "ocr_text": ocr_result.text,
                "ocr_confidence": ocr_result.confidence,
                "extracted_data": parsed_data,
                "processed_at": datetime.now(timezone.utc),
            },
        )
        
        logger.info(
            "OCR processing complete for document %s (confidence: %.2f%%)",
            document_id,
            ocr_result.confidence * 100,
        )
        logger.info(
            "Extracted: %d lab values, %d medications, %d vital signs, %d conditions",
            len(parsed_data.get("lab_values", [])),
            len(parsed_data.get("medications", [])),
            len(parsed_data.get("vital_signs", [])),
            len(parsed_data.get("conditions", [])),
        )
        
        return {
            "document_id": document_id,
            "extracted_text": ocr_result.text,
            "confidence": ocr_result.confidence,
            "engine": ocr_result.engine,
            "word_count": len(ocr_result.text.split()),
            "parsed_data": parsed_data,
        }
    
    async def link_document_to_patient(
        self,
        document_id: str,
        patient_id: str,
    ) -> Dict[str, Any]:
        """Link a document to a patient record."""
        if not self.database_service:
            raise ValueError("Database service required")
        
        await self.database_service.update_document(
            document_id,
            {"patient_id": patient_id},
        )
        
        logger.info("Document %s linked to patient %s", document_id, patient_id)
        
        return {
            "document_id": document_id,
            "patient_id": patient_id,
            "status": "linked",
        }
    
    async def convert_to_fhir_resources(
        self,
        document_id: str,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert parsed document data to FHIR resources.
        
        Args:
            document_id: Document ID
            patient_id: Patient ID (if not provided, will try to get from document)
        
        Returns:
            Dictionary with FHIR resources
        """
        if not self.database_service:
            raise ValueError("Database service required")
        
        # Get document
        document = await self.database_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # Get patient_id
        if not patient_id:
            patient_id = document.get("patient_id")
            if not patient_id:
                raise ValueError("Patient ID required for FHIR conversion")
        
        # Get parsed data
        parsed_data = document.get("extracted_data")
        if not parsed_data:
            raise ValueError("Document has not been processed with OCR yet")
        
        # Convert to FHIR
        fhir_resources = self.fhir_mapper.map_parsed_data_to_fhir(
            parsed_data=parsed_data,
            patient_id=patient_id,
            document_id=document_id,
        )
        
        # Update document with FHIR resource IDs
        fhir_resource_ids = {
            "observation_ids": [obs["id"] for obs in fhir_resources.get("observations", [])],
            "medication_ids": [med["id"] for med in fhir_resources.get("medication_statements", [])],
            "condition_ids": [cond["id"] for cond in fhir_resources.get("conditions", [])],
        }
        
        await self.database_service.update_document(
            document_id,
            {"fhir_resource_id": document_id},  # Store DocumentReference ID
        )
        
        logger.info(
            "Converted to FHIR: %d observations, %d medications, %d conditions",
            len(fhir_resources.get("observations", [])),
            len(fhir_resources.get("medication_statements", [])),
            len(fhir_resources.get("conditions", [])),
        )
        
        return {
            "document_id": document_id,
            "patient_id": patient_id,
            "fhir_resources": fhir_resources,
            "resource_ids": fhir_resource_ids,
        }
    
    async def _prepare_image(self, file_path: str) -> str:
        """
        Convert file to image if needed (PDF -> image).
        
        Returns path to image file.
        """
        path = Path(file_path)
        
        # If already an image, return as-is
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
            return file_path
        
        # If PDF, convert to image
        if path.suffix.lower() == ".pdf":
            try:
                from pdf2image import convert_from_path
                
                # Convert first page to image
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if not images:
                    raise ValueError("Failed to convert PDF to image")
                
                # Save as temporary image
                image_path = path.with_suffix(".png")
                images[0].save(image_path)
                
                logger.info("Converted PDF to image: %s", image_path)
                return str(image_path)
            
            except ImportError:
                raise ImportError(
                    "pdf2image required for PDF processing. "
                    "Install with: pip install pdf2image"
                )
        
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    def _detect_document_type(self, filename: Optional[str]) -> str:
        """Detect document type from filename."""
        if not filename:
            return "unknown"
        
        filename_lower = filename.lower()
        
        if any(term in filename_lower for term in ["lab", "test", "result", "blood"]):
            return "lab_result"
        elif any(term in filename_lower for term in ["prescription", "rx", "med"]):
            return "prescription"
        elif any(term in filename_lower for term in ["note", "note", "report"]):
            return "clinical_note"
        elif any(term in filename_lower for term in ["insurance", "card", "id"]):
            return "insurance_card"
        else:
            return "other"


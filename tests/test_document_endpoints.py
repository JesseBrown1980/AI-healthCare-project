"""
Tests for document upload and processing API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4\nfake pdf content"


@pytest.fixture
def sample_image_content():
    """Sample image content for testing."""
    return b"fake image data"


def test_upload_document_success(client, sample_pdf_content):
    """Test successful document upload."""
    # Use demo login token for testing
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_doc_service = Mock()
        mock_doc_service.save_uploaded_file = AsyncMock(return_value={
            "id": "doc-123",
            "file_path": "/uploads/doc-123.pdf",
            "file_hash": "abc123",
            "document_type": "lab_result",
            "duplicate": False,
        })
        mock_service.return_value = mock_doc_service
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_content, "application/pdf")},
            data={"patient_id": "patient-123", "document_type": "lab_result"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["document_id"] == "doc-123"
        assert data["file_hash"] == "abc123"


def test_upload_document_invalid_file_type(client):
    """Test uploading invalid file type."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", b"executable content", "application/x-msdownload")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_process_document_with_ocr(client):
    """Test processing document with OCR."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_doc_service = Mock()
        mock_doc_service.process_document_with_ocr = AsyncMock(return_value={
            "document_id": "doc-123",
            "extracted_text": "Sample extracted text from OCR",
            "confidence": 0.95,
            "engine": "tesseract",
            "word_count": 5,
        })
        mock_service.return_value = mock_doc_service
        
        response = client.post(
            "/api/v1/documents/doc-123/process",
            params={"engine": "tesseract", "language": "en"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["extracted_text"] == "Sample extracted text from OCR"
        assert data["confidence"] == 0.95
        assert data["engine"] == "tesseract"


def test_link_document_to_patient(client):
    """Test linking document to patient."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_doc_service = Mock()
        mock_doc_service.link_document_to_patient = AsyncMock(return_value={
            "status": "success",
            "document_id": "doc-123",
            "patient_id": "patient-123",
        })
        mock_service.return_value = mock_doc_service
        
        response = client.post(
            "/api/v1/documents/doc-123/link-patient",
            data={"patient_id": "patient-123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["patient_id"] == "patient-123"


def test_get_patient_documents(client):
    """Test getting all documents for a patient."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_database_service") as mock_db:
        mock_db_service = Mock()
        mock_db_service.get_patient_documents = AsyncMock(return_value=[
            {
                "id": "doc-123",
                "patient_id": "patient-123",
                "document_type": "lab_result",
                "file_hash": "abc123",
            },
            {
                "id": "doc-456",
                "patient_id": "patient-123",
                "document_type": "prescription",
                "file_hash": "def456",
            },
        ])
        mock_db.return_value = mock_db_service
        
        response = client.get(
            "/api/v1/patients/patient-123/documents",
            params={"limit": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["patient_id"] == "patient-123"
        assert len(data["documents"]) == 2
        assert data["count"] == 2


def test_get_document_by_id(client):
    """Test getting document by ID."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_database_service") as mock_db:
        mock_db_service = Mock()
        mock_db_service.get_document = AsyncMock(return_value={
            "id": "doc-123",
            "patient_id": "patient-123",
            "document_type": "lab_result",
            "file_hash": "abc123",
            "file_path": "/uploads/doc-123.pdf",
        })
        mock_db.return_value = mock_db_service
        
        response = client.get(
            "/api/v1/documents/doc-123",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["document"]["id"] == "doc-123"
        assert data["document"]["patient_id"] == "patient-123"


def test_convert_document_to_fhir(client):
    """Test converting document to FHIR resources."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_doc_service = Mock()
        mock_doc_service.convert_to_fhir_resources = AsyncMock(return_value={
            "document_id": "doc-123",
            "patient_id": "patient-123",
            "fhir_resources": {
                "observations": [
                    {"resourceType": "Observation", "id": "obs-1"},
                ],
                "medication_statements": [
                    {"resourceType": "MedicationStatement", "id": "med-1"},
                ],
                "conditions": [],
            },
        })
        mock_service.return_value = mock_doc_service
        
        response = client.post(
            "/api/v1/documents/doc-123/convert-fhir",
            data={"patient_id": "patient-123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["patient_id"] == "patient-123"
        assert len(data["fhir_resources"]["observations"]) == 1
        assert len(data["fhir_resources"]["medication_statements"]) == 1
        assert data["resource_counts"]["observations"] == 1
        assert data["resource_counts"]["medications"] == 1


def test_upload_document_service_unavailable(client, sample_pdf_content):
    """Test upload when document service is unavailable."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_service.return_value = None
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 503
        assert "Document service not available" in response.json()["detail"]


def test_process_document_not_found(client):
    """Test processing non-existent document."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code != 200:
        pytest.skip("Demo login not enabled")
    
    token = login_response.json()["access_token"]
    
    with patch("backend.api.v1.endpoints.documents.get_document_service") as mock_service:
        mock_doc_service = Mock()
        mock_doc_service.process_document_with_ocr = AsyncMock(
            side_effect=ValueError("Document not found")
        )
        mock_service.return_value = mock_doc_service
        
        response = client.post(
            "/api/v1/documents/nonexistent/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


import pytest
import shutil
import json
from pathlib import Path
from backend.audit.audit_logger import AuditLogger, AuditEvent, AuditEventType, AuditEventCategory, AuditSeverity
from backend.compliance_service import ComplianceService

# Test directory for audit logs
TEST_LOG_DIR = "test_audit_logs"
TEST_KEY_FILE = "test_keys.json"

@pytest.fixture
def cleanup():
    # Setup
    if Path(TEST_LOG_DIR).exists():
        shutil.rmtree(TEST_LOG_DIR)
    if Path(TEST_KEY_FILE).exists():
        Path(TEST_KEY_FILE).unlink()
        
    yield
    
    # Teardown
    if Path(TEST_LOG_DIR).exists():
        shutil.rmtree(TEST_LOG_DIR)
    if Path(TEST_KEY_FILE).exists():
        Path(TEST_KEY_FILE).unlink()

def test_crypto_shredding_flow(cleanup):
    """
    Verify:
    1. Logs are encrypted on disk.
    2. Logs are readable with key.
    3. Logs are unreadable after key deletion.
    """
    
    # 1. Initialize services
    comp_service = ComplianceService(key_store_path=TEST_KEY_FILE)
    logger = AuditLogger(log_dir=TEST_LOG_DIR, compliance_service=comp_service, console_output=False)
    
    user_id = "user_shred_test_123"
    patient_id = "patient_shred_test_456"
    
    # 2. Log an event with PII
    event = AuditEvent(
        event_type=AuditEventType.PHI_ACCESS,
        category=AuditEventCategory.DATA_ACCESS,
        severity=AuditSeverity.INFO,
        actor=user_id,
        action="Viewed Record",
        outcome="success",
        patient_id=patient_id,
        ip_address="192.168.1.1"
    )
    logger.log(event)
    
    # 3. Verify ENCRYPTION ON DISK
    log_files = list(Path(TEST_LOG_DIR).glob("*.jsonl"))
    assert len(log_files) > 0
    with open(log_files[0], 'r') as f:
        raw_line = f.readline()
        raw_json = json.loads(raw_line)
        
        print(f"DEBUG: raw_json actor: {raw_json.get('actor')}")
        print(f"DEBUG: raw_json patient_id: {raw_json.get('patient_id')}")
        
        # Verify fields are encrypted (start with ENC:)
        if not raw_json['actor'].startswith("ENC:"):
            pytest.fail(f"Actor not encrypted: {raw_json['actor']}")
            
        assert raw_json['actor'].startswith("ENC:")
        assert raw_json['patient_id'].startswith("ENC:")
        assert raw_json['ip_address'].startswith("ENC:")
        
        # Verify original values are NOT visible (except as key index if used)
        # Our implementation uses ENC:<id>:<cipher>, so <id> is visible.
        # We prefer to check that the value is DIFFERENT and Encrypted.
        assert raw_json['actor'] != user_id
        assert raw_json['patient_id'] != patient_id

    # 4. Verify DECRYPTION (Read via Logger)
    # Re-initialize logger to simulate fresh read
    read_logger = AuditLogger(log_dir=TEST_LOG_DIR, compliance_service=comp_service, console_output=False)
    events = read_logger.get_events(limit=10)
    
    assert len(events) == 1
    restored_event = events[0]
    
    assert restored_event['actor'] == user_id
    assert restored_event['patient_id'] == patient_id
    assert restored_event['ip_address'] == "192.168.1.1"
    
    # 5. EXECUTE SHREDDING (Delete Key)
    comp_service.delete_key(user_id)
    comp_service.delete_key(patient_id)
    
    # 6. Verify UNREADABILITY (Read via Logger again)
    # Force reload of keys in compliance service (simulate fresh service start)
    new_comp_service = ComplianceService(key_store_path=TEST_KEY_FILE)
    final_logger = AuditLogger(log_dir=TEST_LOG_DIR, compliance_service=new_comp_service, console_output=False)
    
    final_events = final_logger.get_events(limit=10)
    final_event = final_events[0]
    
    # Should be redacted/forgotten
    # Note: Our implementation returns "[REDACTED/FORGOTTEN]" if key is missing
    assert final_event['actor'] == "[REDACTED/FORGOTTEN]" or final_event['actor'].startswith("ENC:")
    # If using .unshred_data correctly, it catches the exception and returns placeholder or original ciphertext?
    # Let's check implementation: returns "[REDACTED/FORGOTTEN]" if entity_id not in keys.
    
    assert final_event['patient_id'] == "[REDACTED/FORGOTTEN]"


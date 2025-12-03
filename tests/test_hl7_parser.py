"""
Tests for HL7 v2.x message parser.
"""

import pytest
from backend.hl7.message_parser import HL7MessageParser, HL7ParseError


@pytest.fixture
def parser():
    """Create HL7 message parser instance."""
    return HL7MessageParser()


@pytest.fixture
def sample_adt_message():
    """Sample ADT^A01 (Admit) message."""
    return (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5\r"
        "EVN|A01|20240101120000\r"
        "PID|1||123456^^^MRN||DOE^JOHN^MIDDLE||19800101|M|||123 MAIN ST^^CITY^ST^12345||555-1234|||S\r"
        "PV1|1|I|ICU^201^A|||DOC123^SMITH^JOHN|||SUR||||1|||DOC123^SMITH^JOHN|A|||||||||||||||||||HOSPITAL\r"
    )


@pytest.fixture
def sample_oru_message():
    """Sample ORU^R01 (Lab Results) message."""
    return (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456^^^MRN||DOE^JOHN||19800101|M\r"
        "OBR|1||LAB123|CBC^Complete Blood Count|||20240101100000\r"
        "OBX|1|NM|WBC^White Blood Count|1|7.5|10*3/uL|4.0-11.0|N|||F|||20240101100000\r"
        "OBX|2|NM|RBC^Red Blood Count|2|4.5|10*6/uL|4.5-5.5|N|||F|||20240101100000\r"
    )


def test_parse_adt_message(parser, sample_adt_message):
    """Test parsing ADT message."""
    result = parser.parse(sample_adt_message)
    
    assert result["message_type"] == "ADT^A01"
    assert "msh" in result
    assert "pid" in result
    assert "pv1" in result
    
    # Check MSH
    assert result["msh"]["sending_application"] == "ADT"
    assert result["msh"]["receiving_application"] == "AI_SYSTEM"
    
    # Check PID
    assert result["pid"]["patient_id"] == "123456"
    assert result["pid"]["name"]["family"] == "DOE"
    assert result["pid"]["name"]["given"] == "JOHN"
    assert result["pid"]["date_of_birth"] == "19800101"
    assert result["pid"]["gender"] == "M"
    
    # Check PV1
    assert result["pv1"]["patient_class"] == "I"
    assert "ICU" in result["pv1"]["assigned_location"]


def test_parse_oru_message(parser, sample_oru_message):
    """Test parsing ORU message with lab results."""
    result = parser.parse(sample_oru_message)
    
    assert result["message_type"] == "ORU^R01"
    assert "obr" in result
    assert "obx" in result
    assert len(result["obx"]) == 2
    
    # Check first OBX
    obx1 = result["obx"][0]
    assert obx1["observation_id"]["code"] == "WBC"
    assert obx1["observation_id"]["text"] == "White Blood Count"
    assert obx1["observation_value"] == "7.5"
    assert obx1["units"] == "10*3/uL"
    assert obx1["reference_range"] == "4.0-11.0"
    assert obx1["abnormal_flags"] == "N"
    
    # Check second OBX
    obx2 = result["obx"][1]
    assert obx2["observation_id"]["code"] == "RBC"
    assert obx2["observation_value"] == "4.5"


def test_parse_empty_message(parser):
    """Test parsing empty message raises error."""
    with pytest.raises(HL7ParseError):
        parser.parse("")


def test_parse_invalid_message(parser):
    """Test parsing invalid message raises error."""
    with pytest.raises(HL7ParseError):
        parser.parse("INVALID MESSAGE")


def test_parse_missing_msh(parser):
    """Test parsing message without MSH segment raises error."""
    with pytest.raises(HL7ParseError):
        parser.parse("PID|1||123456")


def test_parse_pid_segment(parser):
    """Test parsing PID segment with all fields."""
    message = (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5\r"
        "PID|1||PAT123^^^MRN^MR||SMITH^JANE^ANNE||19900115|F|||456 ST^^TOWN^CA^90210||555-5678\r"
    )
    result = parser.parse(message)
    
    pid = result["pid"]
    assert pid["patient_id"] == "PAT123"
    assert pid["name"]["family"] == "SMITH"
    assert pid["name"]["given"] == "JANE"
    assert pid["name"]["middle"] == "ANNE"
    assert pid["date_of_birth"] == "19900115"
    assert pid["gender"] == "F"


def test_parse_obx_with_different_value_types(parser):
    """Test parsing OBX segments with different value types."""
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
        "OBX|1|NM|GLUCOSE|1|95|mg/dL|70-100|N|||F\r"
        "OBX|2|ST|COMMENT|2|Patient fasting|||N|||F\r"
        "OBX|3|TX|NOTE|3|See physician if symptoms persist|||N|||F\r"
    )
    result = parser.parse(message)
    
    assert len(result["obx"]) == 3
    assert result["obx"][0]["value_type"] == "NM"
    assert result["obx"][1]["value_type"] == "ST"
    assert result["obx"][2]["value_type"] == "TX"

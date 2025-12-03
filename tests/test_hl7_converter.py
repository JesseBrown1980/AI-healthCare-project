"""
Tests for HL7 v2.x to FHIR converter.
"""

import pytest
from backend.hl7.fhir_converter import HL7ToFHIRConverter
from backend.hl7.message_parser import HL7MessageParser


@pytest.fixture
def converter():
    """Create HL7 to FHIR converter instance."""
    return HL7ToFHIRConverter()


@pytest.fixture
def parser():
    """Create HL7 message parser instance."""
    return HL7MessageParser()


@pytest.fixture
def parsed_adt_message(parser):
    """Parse a sample ADT message."""
    message = (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5\r"
        "EVN|A01|20240101120000\r"
        "PID|1||123456^^^MRN||DOE^JOHN||19800101|M\r"
        "PV1|1|I|ICU^201^A|||DOC123^SMITH^JOHN|||SUR||||1|||DOC123^SMITH^JOHN|A|||||||||||||||||||HOSPITAL\r"
    )
    return parser.parse(message)


@pytest.fixture
def parsed_oru_message(parser):
    """Parse a sample ORU message."""
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456^^^MRN||DOE^JOHN||19800101|M\r"
        "OBR|1||LAB123|CBC^Complete Blood Count|||20240101100000\r"
        "OBX|1|NM|6690-2^WBC^LN|1|7.5|10*3/uL|4.0-11.0|N|||F|||20240101100000\r"
        "OBX|2|NM|789-8^RBC^LN|2|4.5|10*6/uL|4.5-5.5|N|||F|||20240101100000\r"
    )
    return parser.parse(message)


def test_convert_patient(converter, parsed_adt_message):
    """Test converting PID to FHIR Patient."""
    resources = converter.convert(parsed_adt_message)
    
    assert resources["patient"] is not None
    patient = resources["patient"]
    
    assert patient["resourceType"] == "Patient"
    assert patient["id"] == "123456"
    assert patient["gender"] == "male"
    assert patient["birthDate"] == "1980-01-01"
    assert len(patient["name"]) == 1
    assert patient["name"][0]["family"] == "DOE"
    assert patient["name"][0]["given"] == ["JOHN"]


def test_convert_observations(converter, parsed_oru_message):
    """Test converting OBX to FHIR Observations."""
    resources = converter.convert(parsed_oru_message)
    
    assert len(resources["observations"]) == 2
    
    obs1 = resources["observations"][0]
    assert obs1["resourceType"] == "Observation"
    assert obs1["status"] == "final"
    assert obs1["code"]["coding"][0]["code"] == "6690-2"
    assert obs1["code"]["coding"][0]["display"] == "WBC"
    assert obs1["valueQuantity"]["value"] == 7.5
    assert obs1["valueQuantity"]["unit"] == "10*3/uL"
    assert "subject" in obs1
    assert obs1["subject"]["reference"] == "Patient/123456"
    
    obs2 = resources["observations"][1]
    assert obs2["valueQuantity"]["value"] == 4.5


def test_convert_encounter(converter, parsed_adt_message):
    """Test converting PV1 to FHIR Encounter."""
    resources = converter.convert(parsed_adt_message)
    
    assert len(resources["encounters"]) == 1
    encounter = resources["encounters"][0]
    
    assert encounter["resourceType"] == "Encounter"
    assert encounter["status"] == "in-progress"
    assert encounter["class"]["code"] == "IMP"
    assert encounter["subject"]["reference"] == "Patient/123456"
    assert "location" in encounter


def test_convert_abnormal_flags(converter, parser):
    """Test converting OBX with abnormal flags."""
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
        "OBX|1|NM|GLUCOSE|1|50|mg/dL|70-100|L|||F\r"
        "OBX|2|NM|GLUCOSE|2|150|mg/dL|70-100|H|||F\r"
    )
    parsed = parser.parse(message)
    resources = converter.convert(parsed)
    
    obs1 = resources["observations"][0]
    assert obs1["interpretation"][0]["coding"][0]["code"] == "L"
    assert obs1["interpretation"][0]["coding"][0]["display"] == "Low"
    
    obs2 = resources["observations"][1]
    assert obs2["interpretation"][0]["coding"][0]["code"] == "H"
    assert obs2["interpretation"][0]["coding"][0]["display"] == "High"


def test_convert_string_observation(converter, parser):
    """Test converting OBX with string value."""
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
        "OBX|1|ST|COMMENT|1|Patient fasting|||N|||F\r"
    )
    parsed = parser.parse(message)
    resources = converter.convert(parsed)
    
    obs = resources["observations"][0]
    assert obs["valueString"] == "Patient fasting"


def test_convert_discharge_encounter(converter, parser):
    """Test converting ADT A03 (discharge) to finished encounter."""
    message = (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A03|12345|P|2.5\r"
        "PID|1||123456\r"
        "PV1|1|I|ICU^201^A|||||||||||||||||||||||||||||||||20240101120000|20240105120000\r"
    )
    parsed = parser.parse(message)
    resources = converter.convert(parsed)
    
    encounter = resources["encounters"][0]
    assert encounter["status"] == "finished"
    assert "period" in encounter
    assert "start" in encounter["period"]
    assert "end" in encounter["period"]


def test_parse_hl7_date(converter):
    """Test HL7 date parsing."""
    assert converter._parse_hl7_date("19800101") == "1980-01-01"
    assert converter._parse_hl7_date("20241225") == "2024-12-25"
    assert converter._parse_hl7_date("") is None
    assert converter._parse_hl7_date("123") is None


def test_parse_hl7_datetime(converter):
    """Test HL7 datetime parsing."""
    assert converter._parse_hl7_datetime("20240101120000") == "2024-01-01T12:00:00Z"
    assert converter._parse_hl7_datetime("20240101") == "2024-01-01"
    assert converter._parse_hl7_datetime("") is None

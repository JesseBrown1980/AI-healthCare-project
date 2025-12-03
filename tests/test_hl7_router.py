"""
Tests for HL7 v2.x message router.
"""

import pytest
from backend.hl7.message_router import HL7MessageRouter
from backend.hl7.message_parser import HL7MessageParser


@pytest.fixture
def router():
    """Create HL7 message router instance."""
    return HL7MessageRouter()


@pytest.fixture
def parser():
    """Create HL7 message parser instance."""
    return HL7MessageParser()


def test_register_handler(router):
    """Test registering a message handler."""
    def handler(message):
        return "processed"
    
    router.register_handler("ADT^A01", handler)
    assert "ADT^A01" in router.get_supported_types()


def test_route_exact_match(router, parser):
    """Test routing with exact message type match."""
    results = []
    
    def adt_handler(message):
        results.append("ADT processed")
        return "ADT result"
    
    router.register_handler("ADT^A01", adt_handler)
    
    message = (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5\r"
        "PID|1||123456\r"
    )
    parsed = parser.parse(message)
    
    result = router.route(parsed)
    assert result == "ADT result"
    assert len(results) == 1


def test_route_wildcard_match(router, parser):
    """Test routing with wildcard message type."""
    results = []
    
    def oru_handler(message):
        results.append("ORU processed")
        return "ORU result"
    
    router.register_handler("ORU^*", oru_handler)
    
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
    )
    parsed = parser.parse(message)
    
    result = router.route(parsed)
    assert result == "ORU result"
    assert len(results) == 1


def test_route_no_handler(router, parser):
    """Test routing when no handler is registered."""
    message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
    )
    parsed = parser.parse(message)
    
    result = router.route(parsed)
    assert result is None


def test_route_multiple_handlers(router, parser):
    """Test routing with multiple registered handlers."""
    adt_results = []
    oru_results = []
    
    def adt_handler(message):
        adt_results.append("ADT")
        return "ADT"
    
    def oru_handler(message):
        oru_results.append("ORU")
        return "ORU"
    
    router.register_handler("ADT^*", adt_handler)
    router.register_handler("ORU^*", oru_handler)
    
    # Route ADT message
    adt_message = (
        "MSH|^~\\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5\r"
        "PID|1||123456\r"
    )
    parsed_adt = parser.parse(adt_message)
    result_adt = router.route(parsed_adt)
    assert result_adt == "ADT"
    assert len(adt_results) == 1
    
    # Route ORU message
    oru_message = (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456\r"
    )
    parsed_oru = parser.parse(oru_message)
    result_oru = router.route(parsed_oru)
    assert result_oru == "ORU"
    assert len(oru_results) == 1


def test_get_supported_types(router):
    """Test getting list of supported message types."""
    router.register_handler("ADT^A01", lambda m: None)
    router.register_handler("ORU^*", lambda m: None)
    router.register_handler("ORM^O01", lambda m: None)
    
    types = router.get_supported_types()
    assert len(types) == 3
    assert "ADT^A01" in types
    assert "ORU^*" in types
    assert "ORM^O01" in types

# HL7 v2.x Integration Expansion Proposal

## Overview

This proposal outlines adding **HL7 v2.x message support** to complement the existing FHIR integration. HL7 v2.x is still widely used in healthcare, especially for real-time interfaces with legacy EHR systems, lab systems, and ADT (Admission/Discharge/Transfer) systems.

## Current State

✅ **FHIR Support** (HL7 FHIR R4)
- RESTful API integration
- SMART-on-FHIR authentication
- Resource-based data model
- Modern, JSON-based

❌ **HL7 v2.x Support** (Missing)
- Message-based interface
- Pipe-delimited format
- Real-time event-driven
- Legacy but still dominant

## Why Add HL7 v2.x?

### 1. **Legacy System Integration**
- Many hospitals still use HL7 v2.x interfaces
- Lab systems often send ORU messages
- ADT systems send patient movement events
- Pharmacy systems use ORM messages

### 2. **Real-Time Event Processing**
- Immediate notifications for:
  - Patient admissions/discharges
  - New lab results
  - Medication orders
  - Critical value alerts

### 3. **Market Coverage**
- FHIR: Modern systems (Epic, Cerner newer versions)
- HL7 v2.x: Legacy systems, labs, pharmacies, ADT systems

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HL7 v2.x Interface                    │
├─────────────────────────────────────────────────────────┤
│  Message Receiver (TCP/MLLP, HTTP, File)                │
│  ↓                                                        │
│  HL7 v2.x Parser (using hl7 library)                     │
│  ↓                                                        │
│  Message Router (by message type: ADT, ORU, ORM, etc.)   │
│  ↓                                                        │
│  FHIR Converter (HL7 v2.x → FHIR Resources)              │
│  ↓                                                        │
│  Existing FHIR Resource Service                           │
│  ↓                                                        │
│  Patient Analyzer & AI Components                        │
└─────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core HL7 v2.x Infrastructure

**Files to Create:**
- `backend/hl7/__init__.py`
- `backend/hl7/message_parser.py` - Parse HL7 v2.x messages
- `backend/hl7/message_router.py` - Route by message type
- `backend/hl7/fhir_converter.py` - Convert HL7 v2.x → FHIR
- `backend/hl7/receiver.py` - Receive messages (TCP/MLLP, HTTP, File)

**Supported Message Types:**
1. **ADT^A01-A60** - Patient administration events
2. **ORU^R01** - Observation results (lab results)
3. **ORM^O01** - Order messages
4. **MDM^T02** - Document management

### Phase 2: API Endpoints

**New Endpoints:**
```
POST /api/v1/hl7/receive
  - Receive HL7 v2.x message
  - Parse and convert to FHIR
  - Trigger patient analysis if needed

GET /api/v1/hl7/messages
  - List received messages
  - Filter by type, patient, date

GET /api/v1/hl7/messages/{id}
  - Get specific message details

POST /api/v1/hl7/send
  - Send HL7 v2.x message (outbound)
```

### Phase 3: Real-Time Processing

- **Event-Driven Analysis**: Auto-analyze patient when new lab results arrive
- **Alert Generation**: Immediate alerts for critical values
- **ADT Integration**: Update patient status on admission/discharge

### Phase 4: Advanced Features

- **MLLP Server**: TCP-based message receiver (standard HL7 interface)
- **Message Acknowledgment**: ACK/NAK handling
- **Message Queuing**: Reliable message processing
- **Retry Logic**: Handle failed conversions

## Example Use Cases

### 1. Lab Results (ORU^R01)
```
HL7 v2.x Message:
MSH|^~\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5
PID|1||123456^^^MRN||DOE^JOHN||19800101|M
OBR|1||LAB123|CBC^Complete Blood Count|||20240101100000
OBX|1|NM|WBC^White Blood Count|1|7.5|10*3/uL|4.0-11.0|N|||F

↓ Convert to FHIR

FHIR Observation:
{
  "resourceType": "Observation",
  "status": "final",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "6690-2",
      "display": "Leukocytes [#/volume] in Blood"
    }]
  },
  "valueQuantity": {
    "value": 7.5,
    "unit": "10*3/uL"
  },
  "referenceRange": [{
    "low": {"value": 4.0},
    "high": {"value": 11.0}
  }]
}
```

### 2. Patient Admission (ADT^A01)
```
HL7 v2.x Message:
MSH|^~\&|ADT|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ADT^A01|12345|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^MRN||DOE^JOHN||19800101|M
PV1|1|I|ICU^201^A|||DOC123^SMITH^JOHN|||SUR||||1|||DOC123^SMITH^JOHN|A|||||||||||||||||||HOSPITAL

↓ Convert to FHIR

FHIR Encounter:
{
  "resourceType": "Encounter",
  "status": "in-progress",
  "class": {
    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
    "code": "IMP",
    "display": "inpatient encounter"
  },
  "type": [{
    "coding": [{
      "code": "ICU",
      "display": "Intensive Care Unit"
    }]
  }],
  "period": {
    "start": "2024-01-01T12:00:00Z"
  }
}
```

## Technical Details

### Dependencies
- `hl7>=0.4.5` (already in requirements)
- `asyncio` for async message processing
- `aiofiles` for file-based message reading

### Message Format
HL7 v2.x uses pipe-delimited segments:
```
MSH|^~\&|SendingApp|SendingFacility|ReceivingApp|ReceivingFacility|...
PID|1|PatientID|...
OBX|1|ValueType|ObservationID|Value|Units|...
```

### Conversion Strategy
1. Parse HL7 v2.x message using `hl7` library
2. Extract relevant data segments
3. Map to FHIR resource structure
4. Use existing FHIR resource service
5. Trigger patient analysis if needed

## Benefits

1. **Broader Integration**: Support both modern (FHIR) and legacy (HL7 v2.x) systems
2. **Real-Time Processing**: Immediate response to clinical events
3. **Market Expansion**: Connect with more healthcare systems
4. **Event-Driven Architecture**: Automatic analysis on new data
5. **Compliance**: Support industry-standard interfaces

## Implementation Effort

- **Phase 1**: ~2-3 days (core parsing and conversion)
- **Phase 2**: ~1-2 days (API endpoints)
- **Phase 3**: ~2-3 days (real-time processing)
- **Phase 4**: ~3-5 days (advanced features)

**Total**: ~8-13 days for full implementation

## Next Steps

1. **Decision**: Approve HL7 v2.x expansion?
2. **Priority**: Which message types first? (Recommend: ORU, ADT)
3. **Interface**: TCP/MLLP, HTTP, or both?
4. **Testing**: Need sample HL7 v2.x messages for testing

## Questions to Consider

1. Do you have access to HL7 v2.x test messages?
2. What message types are most important for your use case?
3. Do you need inbound, outbound, or both?
4. What's the preferred transport (TCP/MLLP, HTTP, File)?

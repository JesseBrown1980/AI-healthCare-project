"""
HL7 v2.x message parser.

Parses pipe-delimited HL7 v2.x messages into structured data.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import hl7
except ImportError:
    hl7 = None
    logging.warning("hl7 library not available. HL7 v2.x support will be limited.")


logger = logging.getLogger(__name__)


class HL7ParseError(Exception):
    """Error parsing HL7 v2.x message."""
    pass


class HL7MessageParser:
    """Parser for HL7 v2.x messages."""
    
    def __init__(self):
        """Initialize HL7 message parser."""
        if hl7 is None:
            raise ImportError("hl7 library is required. Install with: pip install hl7>=0.4.5")
        self.hl7 = hl7
    
    def parse(self, message: str) -> Dict[str, Any]:
        """
        Parse an HL7 v2.x message string.
        
        Args:
            message: Raw HL7 v2.x message (pipe-delimited)
            
        Returns:
            Dictionary containing parsed message structure:
            - message_type: Message type (e.g., "ADT^A01", "ORU^R01")
            - segments: Dictionary of segments by type
            - msh: MSH segment data
            - pid: PID segment data (if present)
            - pv1: PV1 segment data (if present)
            - obr: List of OBR segments (if present)
            - obx: List of OBX segments (if present)
            
        Raises:
            HL7ParseError: If message cannot be parsed
        """
        if not message or not message.strip():
            raise HL7ParseError("Empty message")
        
        try:
            # Parse using hl7 library
            parsed = self.hl7.parse(message)
            
            # Extract MSH segment
            msh = parsed.segment("MSH")
            if not msh:
                raise HL7ParseError("Missing MSH segment")
            
            # Extract message type
            message_type = str(msh[9]) if len(msh) > 9 else None
            if not message_type:
                raise HL7ParseError("Missing message type in MSH.9")
            
            # Build result structure
            result = {
                "message_type": message_type,
                "msh": self._parse_msh(msh),
                "segments": {},
            }
            
            # Extract common segments (handle KeyError when segments don't exist)
            try:
                pid_segments = parsed.segments("PID")
                if pid_segments:
                    result["pid"] = self._parse_pid(pid_segments[0])
                    result["segments"]["PID"] = result["pid"]
            except KeyError:
                pass
            
            try:
                pv1_segments = parsed.segments("PV1")
                if pv1_segments:
                    result["pv1"] = self._parse_pv1(pv1_segments[0])
                    result["segments"]["PV1"] = result["pv1"]
            except KeyError:
                pass
            
            # Extract OBR segments (order information)
            try:
                obr_segments = parsed.segments("OBR")
                if obr_segments:
                    result["obr"] = [self._parse_obr(obr) for obr in obr_segments]
            except KeyError:
                pass
            
            # Extract OBX segments (observations)
            try:
                obx_segments = parsed.segments("OBX")
                if obx_segments:
                    result["obx"] = [self._parse_obx(obx) for obx in obx_segments]
            except KeyError:
                pass
            
            # Extract ORC segments (common order)
            try:
                orc_segments = parsed.segments("ORC")
                if orc_segments:
                    result["orc"] = [self._parse_orc(orc) for orc in orc_segments]
            except KeyError:
                pass
            
            return result
            
        except Exception as e:
            logger.error("Error parsing HL7 message: %s", str(e), exc_info=True)
            raise HL7ParseError(f"Failed to parse HL7 message: {str(e)}") from e
    
    def _parse_msh(self, msh) -> Dict[str, Any]:
        """Parse MSH (Message Header) segment."""
        return {
            "sending_application": str(msh[3]) if len(msh) > 3 else None,
            "sending_facility": str(msh[4]) if len(msh) > 4 else None,
            "receiving_application": str(msh[5]) if len(msh) > 5 else None,
            "receiving_facility": str(msh[6]) if len(msh) > 6 else None,
            "message_datetime": str(msh[7]) if len(msh) > 7 else None,
            "message_type": str(msh[9]) if len(msh) > 9 else None,
            "message_control_id": str(msh[10]) if len(msh) > 10 else None,
            "processing_id": str(msh[11]) if len(msh) > 11 else None,
            "version_id": str(msh[12]) if len(msh) > 12 else None,
        }
    
    def _parse_pid(self, pid) -> Dict[str, Any]:
        """Parse PID (Patient Identification) segment."""
        # Extract patient ID (PID.3 - Patient Identifier List)
        patient_id = None
        patient_id_list = []
        if len(pid) > 3 and pid[3]:
            # PID.3 can be repeated, get first one
            id_component = str(pid[3]).split("^")
            if len(id_component) >= 1:
                patient_id = id_component[0]
                patient_id_list.append({
                    "id": id_component[0],
                    "type": id_component[3] if len(id_component) > 3 else None,
                    "assigning_authority": id_component[4] if len(id_component) > 4 else None,
                })
        
        # Extract name (PID.5 - Patient Name)
        name = {}
        if len(pid) > 5 and pid[5]:
            name_parts = str(pid[5]).split("^")
            name = {
                "family": name_parts[0] if len(name_parts) > 0 else None,
                "given": name_parts[1] if len(name_parts) > 1 else None,
                "middle": name_parts[2] if len(name_parts) > 2 else None,
            }
        
        # Extract DOB (PID.7 - Date/Time of Birth)
        dob = str(pid[7]) if len(pid) > 7 and pid[7] else None
        
        # Extract gender (PID.8 - Administrative Sex)
        gender = str(pid[8]) if len(pid) > 8 and pid[8] else None
        
        return {
            "patient_id": patient_id,
            "patient_id_list": patient_id_list,
            "name": name,
            "date_of_birth": dob,
            "gender": gender,
        }
    
    def _parse_pv1(self, pv1) -> Dict[str, Any]:
        """Parse PV1 (Patient Visit) segment."""
        # PV1 fields: 1=Set ID, 2=Patient Class, 3=Assigned Location, 4=Admission Type
        # 44=Admit Date/Time, 45=Discharge Date/Time
        result = {
            "patient_class": str(pv1[2]) if len(pv1) > 2 and pv1[2] else None,
            "assigned_location": str(pv1[3]) if len(pv1) > 3 and pv1[3] else None,
            "admission_type": str(pv1[4]) if len(pv1) > 4 and pv1[4] else None,
            "attending_doctor": self._parse_xcn(pv1[7]) if len(pv1) > 7 and pv1[7] else None,
        }
        
        # Admit and discharge datetime are at positions 44 and 45
        # But some messages have them at the end - check both
        if len(pv1) > 44 and pv1[44]:
            result["admit_datetime"] = str(pv1[44])
        if len(pv1) > 45 and pv1[45]:
            result["discharge_datetime"] = str(pv1[45])
        
        # Also check end of segment for datetime-like values (for shorter messages)
        # Look for 8+ digit strings that look like dates (YYYYMMDD or YYYYMMDDHHMMSS)
        datetime_candidates = []
        for i in range(len(pv1) - 1, 19, -1):
            if pv1[i]:
                val_str = str(pv1[i])
                # Check if it looks like a datetime (8+ digits)
                if val_str.replace("-", "").replace("+", "").isdigit() and len(val_str.replace("-", "").replace("+", "")) >= 8:
                    datetime_candidates.append((i, val_str))
        
        # Use candidates if standard positions are empty
        if datetime_candidates:
            if "admit_datetime" not in result and len(datetime_candidates) >= 1:
                result["admit_datetime"] = datetime_candidates[-1][1]
            if "discharge_datetime" not in result and len(datetime_candidates) >= 2:
                result["discharge_datetime"] = datetime_candidates[-2][1]
            elif "discharge_datetime" not in result and len(datetime_candidates) >= 1 and "admit_datetime" in result:
                # If we have admit but not discharge, and there's another candidate, use it
                for idx, dt_val in datetime_candidates:
                    if dt_val != result.get("admit_datetime"):
                        result["discharge_datetime"] = dt_val
                        break
        
        return result
    
    def _parse_obr(self, obr) -> Dict[str, Any]:
        """Parse OBR (Observation Request) segment."""
        return {
            "placer_order_number": str(obr[2]) if len(obr) > 2 else None,
            "filler_order_number": str(obr[3]) if len(obr) > 3 else None,
            "universal_service_id": self._parse_ce(obr[4]) if len(obr) > 4 and obr[4] else None,
            "observation_datetime": str(obr[7]) if len(obr) > 7 else None,
            "ordering_provider": self._parse_xcn(obr[16]) if len(obr) > 16 and obr[16] else None,
        }
    
    def _parse_obx(self, obx) -> Dict[str, Any]:
        """Parse OBX (Observation/Result) segment."""
        return {
            "set_id": str(obx[1]) if len(obx) > 1 else None,
            "value_type": str(obx[2]) if len(obx) > 2 else None,
            "observation_id": self._parse_ce(obx[3]) if len(obx) > 3 and obx[3] else None,
            "observation_value": str(obx[5]) if len(obx) > 5 else None,
            "units": str(obx[6]) if len(obx) > 6 else None,
            "reference_range": str(obx[7]) if len(obx) > 7 else None,
            "abnormal_flags": str(obx[8]) if len(obx) > 8 else None,
            "observation_datetime": str(obx[14]) if len(obx) > 14 else None,
            "status": str(obx[11]) if len(obx) > 11 else "F",  # Default to Final
        }
    
    def _parse_orc(self, orc) -> Dict[str, Any]:
        """Parse ORC (Common Order) segment."""
        return {
            "order_control": str(orc[1]) if len(orc) > 1 else None,
            "placer_order_number": str(orc[2]) if len(orc) > 2 else None,
            "filler_order_number": str(orc[3]) if len(orc) > 3 else None,
            "ordering_provider": self._parse_xcn(orc[12]) if len(orc) > 12 and orc[12] else None,
        }
    
    def _parse_ce(self, field) -> Dict[str, Any]:
        """Parse CE (Coded Element) field."""
        if not field:
            return {}
        parts = str(field).split("^")
        return {
            "code": parts[0] if len(parts) > 0 else None,
            "text": parts[1] if len(parts) > 1 else None,
            "coding_system": parts[3] if len(parts) > 3 else None,
        }
    
    def _parse_xcn(self, field) -> Dict[str, Any]:
        """Parse XCN (Extended Composite ID Number and Name) field."""
        if not field:
            return {}
        parts = str(field).split("^")
        return {
            "id": parts[0] if len(parts) > 0 else None,
            "family_name": parts[1] if len(parts) > 1 else None,
            "given_name": parts[2] if len(parts) > 2 else None,
            "middle_name": parts[3] if len(parts) > 3 else None,
        }

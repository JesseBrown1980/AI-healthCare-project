"""
Clinical Graph Builder - Converts Patient FHIR Data to Graph Structure

This module builds graphs from patient clinical data for GNN-based anomaly detection.
Nodes represent: Patients, Medications, Conditions, Providers, Lab Values
Edges represent: Relationships (prescribed, diagnosed, measured, etc.)
"""

import torch
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ClinicalNode:
    """Represents a node in the clinical graph"""
    node_id: str
    node_type: str  # 'patient', 'medication', 'condition', 'provider', 'lab_value'
    features: List[float]
    metadata: Dict[str, Any]


@dataclass
class ClinicalEdge:
    """Represents an edge in the clinical graph"""
    source_id: str
    target_id: str
    edge_type: str  # 'prescribed', 'diagnosed', 'measured', 'interacts_with', 'treats'
    weight: float = 1.0
    metadata: Dict[str, Any] = None


class ClinicalGraphBuilder:
    """
    Converts patient FHIR data into a graph structure for GNN analysis.
    
    Graph Structure:
    - Nodes: Patients, Medications, Conditions, Providers, Lab Values
    - Edges: Clinical relationships (prescribed, diagnosed, measured, etc.)
    """
    
    def __init__(self, feature_dim: int = 16):
        """
        Initialize the clinical graph builder.
        
        Args:
            feature_dim: Dimension of node feature vectors
        """
        self.feature_dim = feature_dim
        self.node_map: Dict[str, int] = {}  # node_id -> node_index
        self.node_types: Dict[str, str] = {}  # node_id -> node_type
        self.node_metadata: Dict[str, Dict[str, Any]] = {}
        
    def _get_or_create_node(self, node_id: str, node_type: str, metadata: Dict[str, Any] = None) -> int:
        """Get or create a node, returning its index"""
        if node_id not in self.node_map:
            self.node_map[node_id] = len(self.node_map)
            self.node_types[node_id] = node_type
            self.node_metadata[node_id] = metadata or {}
        return self.node_map[node_id]
    
    def _create_node_features(self, node_id: str, node_type: str, metadata: Dict[str, Any] = None) -> torch.Tensor:
        """
        Create feature vector for a node based on its type and metadata.
        
        Feature encoding:
        - Type encoding (one-hot-like): patient, medication, condition, provider, lab_value
        - Metadata features: age, severity, dosage, etc.
        """
        features = torch.zeros(self.feature_dim)
        metadata = metadata or {}
        
        # Type-based base features (first 5 dimensions for type encoding)
        type_encodings = {
            'patient': [1.0, 0.0, 0.0, 0.0, 0.0],
            'medication': [0.0, 1.0, 0.0, 0.0, 0.0],
            'condition': [0.0, 0.0, 1.0, 0.0, 0.0],
            'provider': [0.0, 0.0, 0.0, 1.0, 0.0],
            'lab_value': [0.0, 0.0, 0.0, 0.0, 1.0],
        }
        
        type_vec = type_encodings.get(node_type, [0.0] * 5)
        features[:5] = torch.tensor(type_vec[:5])
        
        # Metadata-based features (remaining dimensions)
        if node_type == 'patient':
            # Age normalization (0-100 -> 0-1)
            age = metadata.get('age', 0)
            features[5] = min(age / 100.0, 1.0) if age else 0.0
            
            # Gender encoding
            gender = metadata.get('gender', '').lower()
            features[6] = 1.0 if gender == 'male' else (-1.0 if gender == 'female' else 0.0)
            
        elif node_type == 'medication':
            # Dosage normalization (if available)
            dosage = metadata.get('dosage_value', 0)
            features[5] = min(dosage / 1000.0, 1.0) if dosage else 0.0
            
            # Frequency encoding
            frequency = metadata.get('frequency', '')
            freq_map = {'daily': 1.0, 'twice': 0.8, 'weekly': 0.3, 'as_needed': 0.5}
            features[6] = freq_map.get(frequency.lower(), 0.0)
            
            # High-risk medication flag (anticoagulants, opioids, etc.)
            med_name = metadata.get('name', '').lower()
            high_risk_meds = ['warfarin', 'digoxin', 'lithium', 'methotrexate', 'opioid', 'morphine']
            features[7] = 1.0 if any(risk_med in med_name for risk_med in high_risk_meds) else -1.0
            
        elif node_type == 'condition':
            # Severity encoding
            severity = metadata.get('severity', '').lower()
            severity_map = {'mild': 0.3, 'moderate': 0.6, 'severe': 1.0, 'critical': 1.5}
            features[5] = min(severity_map.get(severity, 0.5), 1.0)  # Cap at 1.0
            
            # Chronic vs acute
            features[6] = 1.0 if metadata.get('chronic', False) else -1.0
            
            # High-risk condition flag (MI, stroke, sepsis, etc.)
            cond_name = metadata.get('name', '').lower()
            high_risk_conditions = ['mi', 'stroke', 'sepsis', 'pulmonary_embolism', 'dvt', 'heart_failure']
            features[7] = 1.0 if any(risk_cond in cond_name for risk_cond in high_risk_conditions) else -1.0
            
        elif node_type == 'lab_value':
            # Value normalization (if reference range available)
            value = metadata.get('value', 0)
            ref_low = metadata.get('reference_range_low', 0)
            ref_high = metadata.get('reference_range_high', 100)
            if ref_high > ref_low:
                normalized = (value - ref_low) / (ref_high - ref_low)
                features[5] = max(0.0, min(1.0, normalized))
            
            # Abnormal flag
            features[6] = 1.0 if metadata.get('abnormal', False) else -1.0
        
        # Add deterministic noise for uniqueness (based on node_id hash)
        torch.manual_seed(hash(node_id) % (2**32))
        noise = torch.randn(self.feature_dim) * 0.05
        features = features + noise
        
        return features
    
    def build_graph_from_patient_data(self, patient_data: Dict[str, Any]) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        """
        Build a graph from patient FHIR data.
        
        Args:
            patient_data: Dictionary containing patient FHIR resources:
                - patient: Patient resource
                - medications: List of MedicationStatement resources
                - conditions: List of Condition resources
                - observations: List of Observation resources (lab values, vitals)
                - encounters: List of Encounter resources (with providers)
        
        Returns:
            x: Node features tensor [num_nodes, feature_dim]
            edge_index: Edge connectivity tensor [2, num_edges]
            graph_metadata: Dictionary with node/edge mappings and metadata
        """
        # Reset state
        self.node_map.clear()
        self.node_types.clear()
        self.node_metadata.clear()
        
        edges: List[Tuple[int, int, str, float]] = []  # (source_idx, target_idx, edge_type, weight)
        edge_metadata: List[Dict[str, Any]] = []
        
        patient_id = patient_data.get('patient', {}).get('id', 'unknown')
        patient_info = patient_data.get('patient', {})
        
        # 1. Create patient node
        patient_age = self._extract_age(patient_info)
        patient_gender = self._extract_gender(patient_info)
        patient_node_id = f"patient_{patient_id}"
        patient_idx = self._get_or_create_node(
            patient_node_id,
            'patient',
            {'age': patient_age, 'gender': patient_gender, 'id': patient_id}
        )
        
        # 2. Process medications
        medications = patient_data.get('medications', [])
        for med in medications:
            med_id = med.get('id', f"med_{len(medications)}")
            med_name = self._extract_medication_name(med)
            med_node_id = f"medication_{med_id}"
            
            # Extract medication metadata
            dosage = self._extract_dosage(med)
            frequency = self._extract_frequency(med)
            
            med_idx = self._get_or_create_node(
                med_node_id,
                'medication',
                {
                    'id': med_id,
                    'name': med_name,
                    'dosage_value': dosage.get('value', 0),
                    'dosage_unit': dosage.get('unit', ''),
                    'frequency': frequency,
                }
            )
            
            # Create edge: patient -> medication (prescribed)
            # Weight based on recency (recent medications weighted higher)
            start_date = self._extract_date(med, 'start')
            recency_weight = self._calculate_recency_weight(start_date)
            edges.append((patient_idx, med_idx, 'prescribed', recency_weight))
            edge_metadata.append({
                'type': 'prescribed',
                'medication_id': med_id,
                'start_date': start_date,
                'recency_weight': recency_weight,
            })
        
        # 3. Process conditions
        conditions = patient_data.get('conditions', [])
        for condition in conditions:
            cond_id = condition.get('id', f"cond_{len(conditions)}")
            cond_name = self._extract_condition_name(condition)
            cond_node_id = f"condition_{cond_id}"
            
            # Extract condition metadata
            severity = self._extract_severity(condition)
            chronic = self._extract_chronic_status(condition)
            
            cond_idx = self._get_or_create_node(
                cond_node_id,
                'condition',
                {
                    'id': cond_id,
                    'name': cond_name,
                    'severity': severity,
                    'chronic': chronic,
                }
            )
            
            # Create edge: patient -> condition (diagnosed)
            # Weight based on recency and severity
            onset_date = self._extract_date(condition, 'onset')
            recency_weight = self._calculate_recency_weight(onset_date)
            severity_weight = 1.2 if severity in ['severe', 'critical'] else 1.0
            edge_weight = min(recency_weight * severity_weight, 1.0)
            edges.append((patient_idx, cond_idx, 'diagnosed', edge_weight))
            edge_metadata.append({
                'type': 'diagnosed',
                'condition_id': cond_id,
                'onset_date': onset_date,
                'recency_weight': recency_weight,
                'severity': severity,
            })
        
        # 4. Process lab values and observations
        observations = patient_data.get('observations', [])
        for obs in observations:
            obs_id = obs.get('id', f"obs_{len(observations)}")
            obs_code = self._extract_observation_code(obs)
            obs_value = self._extract_observation_value(obs)
            obs_node_id = f"lab_value_{obs_id}"
            
            # Extract observation metadata
            ref_range = self._extract_reference_range(obs)
            abnormal = self._is_abnormal(obs_value, ref_range)
            
            obs_idx = self._get_or_create_node(
                obs_node_id,
                'lab_value',
                {
                    'id': obs_id,
                    'code': obs_code,
                    'value': obs_value,
                    'reference_range_low': ref_range.get('low', 0),
                    'reference_range_high': ref_range.get('high', 100),
                    'abnormal': abnormal,
                }
            )
            
            # Create edge: patient -> lab_value (measured)
            # Weight higher for abnormal values and recent measurements
            obs_date = self._extract_date(obs, 'effective')
            recency_weight = self._calculate_recency_weight(obs_date)
            abnormal_weight = 1.3 if abnormal else 1.0
            edge_weight = min(recency_weight * abnormal_weight, 1.0)
            edges.append((patient_idx, obs_idx, 'measured', edge_weight))
            edge_metadata.append({
                'type': 'measured',
                'observation_id': obs_id,
                'date': obs_date,
                'recency_weight': recency_weight,
                'abnormal': abnormal,
            })
        
        # 5. Process providers (from encounters)
        encounters = patient_data.get('encounters', [])
        providers_seen = set()
        for encounter in encounters:
            providers = self._extract_providers(encounter)
            for provider in providers:
                provider_id = provider.get('id', f"provider_{len(providers_seen)}")
                if provider_id not in providers_seen:
                    providers_seen.add(provider_id)
                    provider_name = provider.get('name', 'Unknown')
                    provider_node_id = f"provider_{provider_id}"
                    
                    provider_idx = self._get_or_create_node(
                        provider_node_id,
                        'provider',
                        {
                            'id': provider_id,
                            'name': provider_name,
                            'specialty': provider.get('specialty', ''),
                        }
                    )
                    
                    # Create edge: patient -> provider (visited)
                    edges.append((patient_idx, provider_idx, 'visited', 1.0))
                    edge_metadata.append({
                        'type': 'visited',
                        'provider_id': provider_id,
                        'date': self._extract_date(encounter, 'period.start'),
                    })
        
        # 6. Create medication-medication interaction edges (if multiple medications)
        medication_nodes = [nid for nid, ntype in self.node_types.items() if ntype == 'medication']
        if len(medication_nodes) > 1:
            # Enhanced interaction detection with known drug interactions
            known_interactions = self._get_known_drug_interactions()
            medication_names = {
                med_id: self.node_metadata[med_id].get('name', '').lower()
                for med_id in medication_nodes
            }
            
            for i, med1_id in enumerate(medication_nodes):
                for med2_id in medication_nodes[i+1:]:
                    med1_idx = self.node_map[med1_id]
                    med2_idx = self.node_map[med2_id]
                    med1_name = medication_names[med1_id]
                    med2_name = medication_names[med2_id]
                    
                    # Check for known interactions
                    interaction_severity = self._check_drug_interaction(med1_name, med2_name, known_interactions)
                    
                    if interaction_severity:
                        # Known interaction - higher weight
                        weight = 0.9 if interaction_severity == 'high' else 0.7
                        edges.append((med1_idx, med2_idx, 'interacts_with', weight))
                        edge_metadata.append({
                            'type': 'interacts_with',
                            'medication1': med1_id,
                            'medication2': med2_id,
                            'interaction_severity': interaction_severity,
                            'known_interaction': True,
                        })
                    else:
                        # Potential interaction (polypharmacy) - lower weight
                        edges.append((med1_idx, med2_idx, 'interacts_with', 0.3))
                        edge_metadata.append({
                            'type': 'interacts_with',
                            'medication1': med1_id,
                            'medication2': med2_id,
                            'known_interaction': False,
                            'polypharmacy': True,
                        })
        
        # 6a. Create condition-medication treatment edges
        condition_nodes = [nid for nid, ntype in self.node_types.items() if ntype == 'condition']
        for cond_id in condition_nodes:
            cond_name = self.node_metadata[cond_id].get('name', '').lower()
            cond_idx = self.node_map[cond_id]
            
            # Check if any medications are commonly used to treat this condition
            for med_id in medication_nodes:
                med_name = self.node_metadata[med_id].get('name', '').lower()
                if self._is_treatment_match(cond_name, med_name):
                    med_idx = self.node_map[med_id]
                    edges.append((cond_idx, med_idx, 'treats', 0.8))
                    edge_metadata.append({
                        'type': 'treats',
                        'condition_id': cond_id,
                        'medication_id': med_id,
                        'treatment_match': True,
                    })
        
        # 6b. Create medication-lab value relationships (medications that affect lab values)
        lab_value_nodes = [nid for nid, ntype in self.node_types.items() if ntype == 'lab_value']
        for lab_id in lab_value_nodes:
            lab_code = self.node_metadata[lab_id].get('code', '').lower()
            lab_idx = self.node_map[lab_id]
            
            # Check if any medications are known to affect this lab value
            for med_id in medication_nodes:
                med_name = self.node_metadata[med_id].get('name', '').lower()
                if self._medication_affects_lab(med_name, lab_code):
                    med_idx = self.node_map[med_id]
                    edges.append((med_idx, lab_idx, 'affects', 0.6))
                    edge_metadata.append({
                        'type': 'affects',
                        'medication_id': med_id,
                        'lab_value_id': lab_id,
                        'effect_type': 'known_effect',
                    })
        
        # 7. Build node features
        num_nodes = len(self.node_map)
        x = torch.zeros((num_nodes, self.feature_dim))
        
        for node_id, idx in self.node_map.items():
            node_type = self.node_types[node_id]
            metadata = self.node_metadata.get(node_id, {})
            x[idx] = self._create_node_features(node_id, node_type, metadata)
        
        # 8. Build edge index
        if edges:
            src_indices = [e[0] for e in edges]
            dst_indices = [e[1] for e in edges]
            edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
        else:
            # Empty graph
            edge_index = torch.empty((2, 0), dtype=torch.long)
        
        # 9. Build metadata
        graph_metadata = {
            'node_map': {idx: node_id for node_id, idx in self.node_map.items()},
            'node_types': self.node_types.copy(),
            'node_metadata': self.node_metadata.copy(),
            'edge_types': [e[2] for e in edges],
            'edge_weights': [e[3] for e in edges],
            'edge_metadata': edge_metadata,
            'patient_id': patient_id,
        }
        
        logger.info(
            f"Built clinical graph for patient {patient_id}: "
            f"{num_nodes} nodes, {len(edges)} edges"
        )
        
        return x, edge_index, graph_metadata
    
    # Helper methods for extracting data from FHIR resources
    
    def _extract_age(self, patient: Dict[str, Any]) -> int:
        """Extract age from patient resource"""
        birth_date = patient.get('birthDate')
        if birth_date:
            # Simple age calculation (would need proper date parsing in production)
            try:
                from datetime import datetime
                birth = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
                age = (datetime.now() - birth.replace(tzinfo=None)).days // 365
                return max(0, min(age, 120))
            except:
                pass
        return 0
    
    def _extract_gender(self, patient: Dict[str, Any]) -> str:
        """Extract gender from patient resource"""
        return patient.get('gender', '')
    
    def _extract_medication_name(self, med: Dict[str, Any]) -> str:
        """Extract medication name from MedicationStatement"""
        medication = med.get('medicationCodeableConcept', {})
        coding = medication.get('coding', [{}])
        return coding[0].get('display', '') if coding else ''
    
    def _extract_dosage(self, med: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dosage information from MedicationStatement"""
        dosage = med.get('dosage', [{}])[0] if med.get('dosage') else {}
        dose = dosage.get('dose', {})
        return {
            'value': dose.get('value', 0),
            'unit': dose.get('unit', ''),
        }
    
    def _extract_frequency(self, med: Dict[str, Any]) -> str:
        """Extract frequency from MedicationStatement"""
        dosage = med.get('dosage', [{}])[0] if med.get('dosage') else {}
        timing = dosage.get('timing', {})
        repeat = timing.get('repeat', {})
        return repeat.get('frequency', '')
    
    def _extract_condition_name(self, condition: Dict[str, Any]) -> str:
        """Extract condition name from Condition"""
        code = condition.get('code', {})
        coding = code.get('coding', [{}])
        return coding[0].get('display', '') if coding else ''
    
    def _extract_severity(self, condition: Dict[str, Any]) -> str:
        """Extract severity from Condition"""
        severity = condition.get('severity', {})
        coding = severity.get('coding', [{}])
        return coding[0].get('display', '').lower() if coding else ''
    
    def _extract_chronic_status(self, condition: Dict[str, Any]) -> bool:
        """Determine if condition is chronic"""
        category = condition.get('category', [{}])
        if category:
            coding = category[0].get('coding', [{}])
            if coding:
                code = coding[0].get('code', '')
                return code in ['chronic', '55607006']  # SNOMED chronic code
        return False
    
    def _extract_observation_code(self, obs: Dict[str, Any]) -> str:
        """Extract observation code"""
        code = obs.get('code', {})
        coding = code.get('coding', [{}])
        return coding[0].get('code', '') if coding else ''
    
    def _extract_observation_value(self, obs: Dict[str, Any]) -> float:
        """Extract observation value"""
        value = obs.get('valueQuantity', {})
        return value.get('value', 0.0) if value else 0.0
    
    def _extract_reference_range(self, obs: Dict[str, Any]) -> Dict[str, float]:
        """Extract reference range from Observation"""
        ranges = obs.get('referenceRange', [{}])
        if ranges:
            ref_range = ranges[0]
            low = ref_range.get('low', {}).get('value', 0)
            high = ref_range.get('high', {}).get('value', 100)
            return {'low': float(low), 'high': float(high)}
        return {'low': 0.0, 'high': 100.0}
    
    def _is_abnormal(self, value: float, ref_range: Dict[str, float]) -> bool:
        """Check if observation value is abnormal"""
        low = ref_range.get('low', 0)
        high = ref_range.get('high', 100)
        return value < low or value > high
    
    def _extract_providers(self, encounter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract providers from Encounter"""
        participants = encounter.get('participant', [])
        providers = []
        for participant in participants:
            individual = participant.get('individual', {})
            if individual:
                providers.append({
                    'id': individual.get('reference', '').split('/')[-1],
                    'name': individual.get('display', 'Unknown'),
                    'specialty': '',  # Would need to fetch from Practitioner resource
                })
        return providers
    
    def _extract_date(self, resource: Dict[str, Any], field: str) -> Optional[str]:
        """Extract date from resource"""
        if field == 'start':
            return resource.get('effectivePeriod', {}).get('start')
        elif field == 'onset':
            return resource.get('onsetDateTime') or resource.get('onsetPeriod', {}).get('start')
        elif field == 'effective':
            return resource.get('effectiveDateTime') or resource.get('effectivePeriod', {}).get('start')
        elif field == 'period.start':
            return resource.get('period', {}).get('start')
        return None
    
    def _calculate_recency_weight(self, date_str: Optional[str]) -> float:
        """
        Calculate edge weight based on recency of the event.
        More recent events get higher weights (closer to 1.0).
        Older events get lower weights (closer to 0.3).
        """
        if not date_str:
            return 0.5  # Default weight for missing dates
        
        try:
            from datetime import datetime, timezone
            event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_ago = (now - event_date).days
            
            # Weight decay: recent (0-30 days) = 1.0, older (365+ days) = 0.3
            if days_ago <= 30:
                return 1.0
            elif days_ago <= 90:
                return 0.8
            elif days_ago <= 180:
                return 0.6
            elif days_ago <= 365:
                return 0.4
            else:
                return 0.3
        except Exception:
            return 0.5  # Default on parsing error
    
    def _get_known_drug_interactions(self) -> Dict[Tuple[str, str], str]:
        """
        Returns a dictionary of known drug interactions.
        Key: (drug1, drug2) tuple (normalized names)
        Value: 'high', 'medium', or 'low' severity
        """
        return {
            # High severity interactions
            ('warfarin', 'nsaid'): 'high',
            ('warfarin', 'aspirin'): 'high',
            ('warfarin', 'ibuprofen'): 'high',
            ('digoxin', 'amiodarone'): 'high',
            ('lithium', 'diuretic'): 'high',
            ('methotrexate', 'nsaid'): 'high',
            
            # Medium severity interactions
            ('lisinopril', 'potassium'): 'medium',
            ('ace_inhibitor', 'potassium'): 'medium',
            ('metformin', 'dye'): 'medium',
            ('metformin', 'contrast'): 'medium',
            ('statins', 'grapefruit'): 'medium',
            ('cyclosporine', 'grapefruit'): 'medium',
            
            # Common interactions
            ('aspirin', 'nsaid'): 'medium',
            ('aspirin', 'warfarin'): 'high',
            ('beta_blocker', 'calcium_channel_blocker'): 'medium',
        }
    
    def _check_drug_interaction(self, med1: str, med2: str, known_interactions: Dict[Tuple[str, str], str]) -> Optional[str]:
        """Check if two medications have a known interaction"""
        # Normalize medication names
        med1_norm = med1.replace(' ', '_').replace('-', '_')
        med2_norm = med2.replace(' ', '_').replace('-', '_')
        
        # Check both orderings
        key1 = (med1_norm, med2_norm)
        key2 = (med2_norm, med1_norm)
        
        if key1 in known_interactions:
            return known_interactions[key1]
        if key2 in known_interactions:
            return known_interactions[key2]
        
        # Check for partial matches (e.g., "warfarin" in "warfarin_sodium")
        for (drug1, drug2), severity in known_interactions.items():
            if drug1 in med1_norm and drug2 in med2_norm:
                return severity
            if drug1 in med2_norm and drug2 in med1_norm:
                return severity
        
        return None
    
    def _is_treatment_match(self, condition_name: str, medication_name: str) -> bool:
        """
        Check if a medication is commonly used to treat a condition.
        This is a simplified heuristic - in production, use a medical knowledge base.
        """
        treatment_mappings = {
            # Hypertension
            'hypertension': ['lisinopril', 'amlodipine', 'metoprolol', 'hydrochlorothiazide', 'ace', 'arb'],
            'high_blood_pressure': ['lisinopril', 'amlodipine', 'metoprolol', 'hydrochlorothiazide'],
            
            # Diabetes
            'diabetes': ['metformin', 'insulin', 'glipizide', 'glyburide'],
            'diabetes_mellitus': ['metformin', 'insulin'],
            
            # Heart conditions
            'heart_failure': ['lisinopril', 'carvedilol', 'furosemide', 'digoxin'],
            'atrial_fibrillation': ['warfarin', 'apixaban', 'rivaroxaban', 'metoprolol'],
            
            # Infections
            'infection': ['antibiotic', 'amoxicillin', 'azithromycin'],
            'pneumonia': ['antibiotic', 'amoxicillin', 'azithromycin'],
        }
        
        condition_norm = condition_name.replace(' ', '_').replace('-', '_').lower()
        med_norm = medication_name.replace(' ', '_').replace('-', '_').lower()
        
        for cond_key, meds in treatment_mappings.items():
            if cond_key in condition_norm:
                if any(med in med_norm for med in meds):
                    return True
        
        return False
    
    def _medication_affects_lab(self, medication_name: str, lab_code: str) -> bool:
        """
        Check if a medication is known to affect a lab value.
        This is a simplified heuristic - in production, use a medical knowledge base.
        """
        medication_norm = medication_name.replace(' ', '_').replace('-', '_').lower()
        lab_norm = lab_code.replace(' ', '_').replace('-', '_').lower()
        
        # Known medication-lab effects
        medication_lab_effects = {
            # Medications affecting kidney function
            'nsaid': ['creatinine', 'bun', 'egfr'],
            'ace_inhibitor': ['creatinine', 'potassium'],
            'arb': ['creatinine', 'potassium'],
            'diuretic': ['creatinine', 'sodium', 'potassium'],
            
            # Medications affecting liver function
            'statin': ['alt', 'ast', 'liver'],
            'acetaminophen': ['alt', 'ast', 'liver'],
            
            # Medications affecting blood glucose
            'steroid': ['glucose', 'blood_sugar'],
            'prednisone': ['glucose', 'blood_sugar'],
            
            # Medications affecting INR/coagulation
            'warfarin': ['inr', 'pt', 'coagulation'],
            'heparin': ['inr', 'pt', 'coagulation'],
            
            # Medications affecting electrolytes
            'diuretic': ['sodium', 'potassium', 'magnesium'],
            'ace_inhibitor': ['potassium'],
        }
        
        for med_key, affected_labs in medication_lab_effects.items():
            if med_key in medication_norm:
                if any(lab in lab_norm for lab in affected_labs):
                    return True
        
        return False


"""
S-LoRA (Sparse LoRA) Manager Module
Manages efficient parameter-tuned adapters for different medical specialties
Optimizes attention mechanisms for long medical records
"""

import logging
from typing import Dict, List, Optional, Any, Set
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class SLoRAManager:
    """
    Manages Sparse LoRA (Low-Rank Adapter) system for efficient fine-tuning
    
    Key benefits:
    - Multiple specialty adapters (~100MB each) vs. full model copies (2-13GB)
    - Dynamic composition for multi-specialty patient cases
    - Efficient long-sequence processing (multi-year patient histories)
    - Rapid adaptation to new specialties
    """
    
    def __init__(self, adapter_path: str, base_model: str):
        """
        Initialize S-LoRA Manager
        
        Args:
            adapter_path: Directory where adapters are stored
            base_model: Base LLM model identifier
        """
        self.adapter_path = adapter_path
        self.base_model = base_model
        self.adapters: Dict[str, Dict] = {}
        self.active_adapters: Set[str] = set()
        self.adapter_memory: Dict[str, float] = {}
        self.specialties_map: Dict[str, str] = {}
        
        self._initialize_adapters()
        
        logger.info(f"S-LoRA Manager initialized with base model: {base_model}")
    
    def _initialize_adapters(self):
        """Initialize available adapters"""
        # Define core medical specialty adapters
        specialties = {
            "cardiology": "Cardiac health, heart disease, hypertension",
            "oncology": "Cancer diagnosis, treatment, chemotherapy",
            "neurology": "Brain, nervous system, seizures, neurodegeneration",
            "endocrinology": "Diabetes, thyroid, hormonal disorders",
            "pulmonology": "Lung disease, respiratory, asthma, COPD",
            "gastroenterology": "GI tract, liver, digestive diseases",
            "nephrology": "Kidney disease, renal function, dialysis",
            "rheumatology": "Autoimmune, arthritis, connective tissue diseases",
            "infectious_disease": "Infections, antibiotics, viral diseases",
            "psychiatry": "Mental health, depression, anxiety, psychosis",
        }
        
        for specialty, description in specialties.items():
            adapter_name = f"adapter_{specialty}"
            self.adapters[adapter_name] = {
                "name": adapter_name,
                "specialty": specialty,
                "description": description,
                "parameters": 1024 * 1024 * 100,  # ~100MB per adapter (LoRA)
                "rank": 8,
                "lora_alpha": 16,
                "status": "available",
                "loaded": False,
                "accuracy_score": 0.92 + (hash(specialty) % 100) / 1000,  # Mock accuracy
                "last_trained": datetime.now().isoformat()
            }
            self.specialties_map[specialty] = adapter_name
            self.adapter_memory[adapter_name] = 100.0  # MB
        
        logger.info(f"Initialized {len(self.adapters)} medical specialty adapters")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current S-LoRA status"""
        total_memory = sum(self.adapter_memory.values()) / 1024  # Convert to GB
        used_memory = sum(
            self.adapter_memory[a] for a in self.active_adapters
        ) / 1024  # GB for active only
        
        return {
            "active": list(self.active_adapters),
            "available": list(self.adapters.keys()),
            "memory": {
                "total_available": total_memory,
                "used_by_active": used_memory,
                "efficiency": (used_memory / total_memory) * 100 if total_memory > 0 else 0
            },
            "specialties": {
                spec: self.specialties_map.get(spec) 
                for spec in self.specialties_map.keys()
            }
        }
    
    async def select_adapters(
        self,
        specialties: List[str],
        patient_data: Optional[Dict] = None
    ) -> List[str]:
        """
        Intelligently select and compose adapters for patient case
        
        Args:
            specialties: List of medical specialties relevant to patient
            patient_data: Patient clinical data for contextual selection
            
        Returns:
            List of adapter names to activate
        """
        logger.info(f"Selecting adapters for specialties: {specialties}")
        
        selected = []
        
        # 1. Direct mapping of requested specialties
        for specialty in specialties:
            if specialty in self.specialties_map:
                adapter = self.specialties_map[specialty]
                selected.append(adapter)
        
        # 2. Intelligent secondary selection based on patient data
        if patient_data:
            secondary = await self._infer_specialties(patient_data)
            for spec in secondary:
                if spec in self.specialties_map:
                    adapter = self.specialties_map[spec]
                    if adapter not in selected:
                        selected.append(adapter)
        
        # 3. Rank by relevance score
        selected = self._rank_adapters(selected, patient_data)
        
        logger.info(f"Selected adapters: {selected}")
        return selected
    
    async def _infer_specialties(self, patient_data: Dict) -> List[str]:
        """Infer relevant specialties from patient data"""
        inferred = []
        
        # Analyze conditions for specialty hints
        if patient_data.get("conditions"):
            condition_keywords = {
                "cardiology": ["heart", "cardiac", "MI", "hypertension", "arrhythmia"],
                "oncology": ["cancer", "tumor", "leukemia", "lymphoma"],
                "neurology": ["seizure", "stroke", "dementia", "Parkinson"],
                "endocrinology": ["diabetes", "thyroid", "hormone"],
                "pulmonology": ["asthma", "COPD", "pneumonia", "lung"],
                "gastroenterology": ["liver", "GI", "Crohn", "colitis"],
                "nephrology": ["kidney", "renal", "glomerulo", "proteinuria"],
                "infectious_disease": ["infection", "sepsis", "viral"]
            }
            
            for condition in patient_data["conditions"]:
                code = condition.get("code", "").lower()
                for specialty, keywords in condition_keywords.items():
                    if any(kw in code for kw in keywords):
                        if specialty not in inferred:
                            inferred.append(specialty)
        
        # Analyze medications for specialty hints
        if patient_data.get("medications"):
            med_keywords = {
                "cardiology": ["beta-blocker", "ACE", "statin", "nitrate"],
                "endocrinology": ["insulin", "metformin", "GLP-1"],
                "pulmonology": ["bronchodilator", "corticosteroid"],
                "psychiatry": ["antidepressant", "antipsychotic", "anxiolytic"]
            }
            
            for med in patient_data["medications"]:
                med_name = med.get("medication", "").lower()
                for specialty, keywords in med_keywords.items():
                    if any(kw in med_name for kw in keywords):
                        if specialty not in inferred:
                            inferred.append(specialty)
        
        return inferred
    
    def _rank_adapters(self, adapters: List[str], patient_data: Optional[Dict] = None) -> List[str]:
        """Rank adapters by relevance"""
        scores = {}
        
        for adapter in adapters:
            score = self.adapters[adapter].get("accuracy_score", 0.9)
            
            # Boost primary adapters (first in list)
            if adapters.index(adapter) == 0:
                score *= 1.2
            
            scores[adapter] = score
        
        # Sort by relevance score (descending)
        ranked = sorted(adapters, key=lambda x: scores[x], reverse=True)
        return ranked
    
    async def activate_adapter(self, adapter_name: str, specialty: Optional[str] = None) -> bool:
        """
        Activate a LoRA adapter
        
        Args:
            adapter_name: Name of adapter to activate
            specialty: Optional specialty for context
            
        Returns:
            True if successfully activated
        """
        try:
            if adapter_name not in self.adapters:
                logger.warning(f"Adapter not found: {adapter_name}")
                return False
            
            # Check memory constraint
            current_memory = sum(
                self.adapter_memory.get(a, 0) for a in self.active_adapters
            )
            adapter_memory = self.adapter_memory.get(adapter_name, 100)
            
            if current_memory + adapter_memory > 2000:  # Max 2GB
                logger.warning("Memory limit exceeded, removing least-used adapter")
                await self._evict_adapter()
            
            self.active_adapters.add(adapter_name)
            self.adapters[adapter_name]["loaded"] = True
            self.adapters[adapter_name]["status"] = "active"
            
            logger.info(f"Activated adapter: {adapter_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error activating adapter: {str(e)}")
            return False
    
    async def deactivate_adapter(self, adapter_name: str) -> bool:
        """Deactivate a LoRA adapter"""
        try:
            if adapter_name in self.active_adapters:
                self.active_adapters.remove(adapter_name)
                self.adapters[adapter_name]["loaded"] = False
                self.adapters[adapter_name]["status"] = "available"
                
                logger.info(f"Deactivated adapter: {adapter_name}")
                return True
            return False
        
        except Exception as e:
            logger.error(f"Error deactivating adapter: {str(e)}")
            return False
    
    async def _evict_adapter(self) -> bool:
        """Evict least-used adapter to free memory"""
        if self.active_adapters:
            # Simple strategy: remove first active adapter
            to_evict = list(self.active_adapters)[0]
            return await self.deactivate_adapter(to_evict)
        return False
    
    async def compose_adapters(self, adapter_names: List[str], weights: Optional[List[float]] = None) -> Dict:
        """
        Compose multiple adapters for sophisticated multi-specialty handling
        
        Args:
            adapter_names: List of adapters to compose
            weights: Relative weights for blending (defaults to equal)
            
        Returns:
            Composed adapter configuration
        """
        if not weights:
            weights = [1.0 / len(adapter_names)] * len(adapter_names)
        
        logger.info(f"Composing adapters: {adapter_names} with weights: {weights}")
        
        composition = {
            "composed_name": f"composition_{'_'.join(adapter_names[:2])}",
            "component_adapters": adapter_names,
            "weights": weights,
            "created_at": datetime.now().isoformat(),
            "composed_rank": sum(
                self.adapters[a].get("rank", 8) for a in adapter_names
            ),
            "estimated_memory": sum(
                self.adapter_memory.get(a, 100) * w 
                for a, w in zip(adapter_names, weights)
            )
        }
        
        return composition
    
    def get_stats(self) -> Dict:
        """Get S-LoRA system statistics"""
        total_adapters = len(self.adapters)
        loaded = sum(1 for a in self.adapters.values() if a.get("loaded"))
        
        return {
            "total_adapters": total_adapters,
            "loaded_adapters": loaded,
            "active_adapters": len(self.active_adapters),
            "memory_efficiency": (
                sum(self.adapter_memory.get(a, 0) for a in self.active_adapters) / 
                (loaded * 100) * 100 if loaded > 0 else 0
            ),
            "specialties_covered": len(self.specialties_map)
        }

"""
RAG-Fusion Component
Retrieval-Augmented Generation with medical knowledge bases
Integrates clinical guidelines, literature, and protocols
Supports region-specific knowledge filtering for compliance
"""

import logging
from typing import Dict, List, Optional, Any
import os
import json
from datetime import datetime

from backend.config.compliance_policies import get_region

logger = logging.getLogger(__name__)


class RAGFusion:
    """
    Retrieval-Augmented Generation component for medical knowledge
    Connects to medical literature, guidelines, and clinical databases
    """
    
    def __init__(self, knowledge_base_path: str, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize RAG-Fusion component
        
        Args:
            knowledge_base_path: Path to medical knowledge base
            embedding_model: Embedding model for semantic search
        """
        self.knowledge_base_path = knowledge_base_path
        self.embedding_model = embedding_model
        self.embeddings = None
        self.knowledge_index = None
        self.retrieval_stats = []
        self.region = get_region()  # Get current deployment region
        
        self._initialize_embeddings()
        self._load_knowledge_base()
        
        logger.info(f"RAG-Fusion component initialized (region: {self.region})")
    
    def _initialize_embeddings(self):
        """Initialize embedding model for semantic similarity"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embeddings = SentenceTransformer(self.embedding_model)
            logger.info(f"Embedding model loaded: {self.embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Using mock embeddings.")
            self.embeddings = None
        except Exception as exc:
            logger.warning(
                "Unable to initialize embedding model '%s': %s. Using mock embeddings instead.",
                self.embedding_model,
                exc,
            )
            self.embeddings = None
    
    def _load_knowledge_base(self):
        """Load medical knowledge base"""
        try:
            # Initialize in-memory knowledge base
            # In production, this could be a vector database (Pinecone, Milvus, etc.)
            self.knowledge_index = {
                "guidelines": self._load_guidelines(),
                "protocols": self._load_protocols(),
                "conditions": self._load_conditions_kb(),
                "drugs": self._load_drug_database()
            }
            logger.info("Medical knowledge base loaded successfully")
        except Exception as e:
            logger.warning(f"Error loading knowledge base: {str(e)}")
            self.knowledge_index = {"guidelines": [], "protocols": [], "conditions": {}, "drugs": {}}
    
    def _load_guidelines(self) -> List[Dict]:
        """Load clinical guidelines with region tags"""
        return [
            {
                "id": "guideline_001",
                "title": "Hypertension Management",
                "source": "ACC/AHA 2023",
                "content": "First-line agents: ACE-I, ARB, CCB, or thiazide diuretics...",
                "regions": ["US", "DEFAULT"],  # US-specific guidelines
            },
            {
                "id": "guideline_002",
                "title": "Diabetes Type 2 Management",
                "source": "ADA 2024",
                "content": "Initial therapy often includes metformin unless contraindicated...",
                "regions": ["US", "DEFAULT"],
            },
            {
                "id": "guideline_003",
                "title": "Hypertension Management (EU)",
                "source": "ESC/ESH 2023",
                "content": "European guidelines for hypertension: ACE-I, ARB, or CCB as first-line...",
                "regions": ["EU", "DEFAULT"],
            },
            {
                "id": "guideline_004",
                "title": "Diabetes Management (EU)",
                "source": "EASD/ADA 2024",
                "content": "European diabetes guidelines: metformin first-line, consider SGLT2 inhibitors...",
                "regions": ["EU", "DEFAULT"],
            },
        ]
    
    def _load_protocols(self) -> List[Dict]:
        """Load clinical protocols with region tags"""
        return [
            {
                "id": "protocol_001",
                "title": "Sepsis Management",
                "source": "Surviving Sepsis",
                "steps": ["Blood cultures", "Broad-spectrum antibiotics", "Fluid resuscitation"],
                "regions": ["US", "EU", "DEFAULT"],  # Universal protocol
            },
            {
                "id": "protocol_002",
                "title": "Antibiotic Stewardship (EU)",
                "source": "ECDC Guidelines",
                "steps": ["Culture before antibiotics", "Narrow spectrum when possible", "Review after 48h"],
                "regions": ["EU", "DEFAULT"],
            },
        ]
    
    def _load_conditions_kb(self) -> Dict:
        """Load condition-specific knowledge with region tags"""
        return {
            "hypertension": {
                "definition": "Sustained elevation of blood pressure",
                "risk_factors": ["age", "family_history", "obesity", "salt_intake"],
                "complications": ["MI", "stroke", "kidney_disease", "heart_failure"],
                "regions": ["US", "EU", "APAC", "DEFAULT"],  # Universal condition
            },
            "diabetes": {
                "definition": "Metabolic disorder characterized by hyperglycemia",
                "types": ["type1", "type2", "gestational"],
                "monitoring": ["HbA1c", "fasting_glucose", "lipid_panel"],
                "regions": ["US", "EU", "APAC", "DEFAULT"],  # Universal condition
            }
        }
    
    def _load_drug_database(self) -> Dict:
        """Load drug database with interactions and region-specific availability"""
        return {
            "metformin": {
                "class": "biguanide",
                "indication": "Type 2 diabetes",
                "contraindications": ["eGFR < 30", "liver_disease"],
                "interactions": ["contrast_dye", "certain_antibiotics"],
                "regions": ["US", "EU", "APAC", "DEFAULT"],  # Widely available
            },
            "lisinopril": {
                "class": "ACE-inhibitor",
                "indication": "Hypertension, heart failure",
                "side_effects": ["dry_cough", "hyperkalemia"],
                "monitoring": ["K+", "creatinine"],
                "regions": ["US", "EU", "APAC", "DEFAULT"],  # Widely available
            }
        }
    
    async def retrieve_relevant_knowledge(self, query: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve relevant medical knowledge for a query, filtered by region.
        
        Args:
            query: Medical question or topic
            region: Optional region code to filter by (uses instance region if not provided)
            
        Returns:
            Dictionary with relevant guidelines, protocols, and sources (region-filtered)
        """
        if region is None:
            region = self.region
        
        logger.info(f"Retrieving knowledge for: {query[:50]}... (region: {region})")
        
        try:
            results = {
                "query": query,
                "region": region,
                "relevant_content": [],
                "sources": [],
                "guidelines": [],
                "protocols": [],
                "drug_info": [],
                "confidence_scores": [],
                "retrieved_at": datetime.now().isoformat()
            }
            
            # 1. Search guidelines (region-filtered)
            guideline_results = self._search_guidelines(query, region=region)
            results["guidelines"].extend(guideline_results)
            for g in guideline_results:
                results["relevant_content"].append(f"Guideline ({g['source']}): {g['content'][:200]}")
                results["sources"].append(g["source"])
            
            # 2. Search protocols (region-filtered)
            protocol_results = self._search_protocols(query, region=region)
            results["protocols"].extend(protocol_results)
            for p in protocol_results:
                results["relevant_content"].append(f"Protocol ({p['title']}): {', '.join(p.get('steps', []))}")
                results["sources"].append(p["title"])
            
            # 3. Search condition knowledge (region-filtered)
            condition_results = self._search_conditions(query, region=region)
            for cond, info in condition_results.items():
                results["relevant_content"].append(f"Condition ({cond}): {json.dumps(info)[:200]}")
                results["sources"].append(f"Condition DB: {cond}")
            
            # 4. Search drug database (region-filtered)
            drug_results = self._search_drugs(query, region=region)
            results["drug_info"].extend(drug_results)
            for drug, info in drug_results:
                results["relevant_content"].append(f"Drug ({drug}): {json.dumps(info)[:200]}")
                results["sources"].append(f"Drug DB: {drug}")
            
            # 5. Semantic search if embeddings available
            semantic_results = await self._semantic_search(query)
            results["relevant_content"].extend(semantic_results.get("content", []))
            results["sources"].extend(semantic_results.get("sources", []))
            
            # Track retrieval statistics
            self.retrieval_stats.append({
                "query": query,
                "results_count": len(results["relevant_content"]),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Retrieved {len(results['relevant_content'])} relevant items")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {str(e)}")
            return {"error": str(e), "query": query, "relevant_content": []}
    
    def _search_guidelines(self, query: str, region: Optional[str] = None) -> List[Dict]:
        """
        Search clinical guidelines, filtered by region if specified.
        
        Args:
            query: Search query
            region: Optional region code to filter by (uses instance region if not provided)
        """
        if region is None:
            region = self.region
        
        keywords = query.lower().split()
        matching = []
        
        for guideline in self.knowledge_index.get("guidelines", []):
            # Check region compatibility
            guideline_regions = guideline.get("regions", ["DEFAULT"])
            if region not in guideline_regions and "DEFAULT" not in guideline_regions:
                continue  # Skip guidelines not for this region
            
            # Check keyword match
            if any(kw in guideline.get("title", "").lower() or 
                   kw in guideline.get("content", "").lower() 
                   for kw in keywords):
                matching.append(guideline)
        
        return matching
    
    def _search_protocols(self, query: str, region: Optional[str] = None) -> List[Dict]:
        """
        Search clinical protocols, filtered by region if specified.
        
        Args:
            query: Search query
            region: Optional region code to filter by (uses instance region if not provided)
        """
        if region is None:
            region = self.region
        
        keywords = query.lower().split()
        matching = []
        
        for protocol in self.knowledge_index.get("protocols", []):
            # Check region compatibility
            protocol_regions = protocol.get("regions", ["DEFAULT"])
            if region not in protocol_regions and "DEFAULT" not in protocol_regions:
                continue  # Skip protocols not applicable to this region
            
            # Check keyword match
            if any(kw in protocol.get("title", "").lower() for kw in keywords):
                matching.append(protocol)
        
        return matching
    
    def _search_conditions(self, query: str) -> Dict:
        """Search condition knowledge base"""
        keywords = query.lower().split()
        matching = {}
        
        for condition, info in self.knowledge_index.get("conditions", {}).items():
            if any(kw in condition.lower() for kw in keywords):
                matching[condition] = info
        
        return matching
    
    def _search_drugs(self, query: str, region: Optional[str] = None) -> List[tuple]:
        """
        Search drug database, filtered by region if specified.
        
        Args:
            query: Search query
            region: Optional region code to filter by (uses instance region if not provided)
        """
        if region is None:
            region = self.region
        
        keywords = query.lower().split()
        matching = []
        
        for drug, info in self.knowledge_index.get("drugs", {}).items():
            # Check region compatibility (drug availability may vary by region)
            drug_regions = info.get("regions", ["DEFAULT"])
            if region not in drug_regions and "DEFAULT" not in drug_regions:
                continue  # Skip drugs not available in this region
            
            # Check keyword match
            if any(kw in drug.lower() or 
                   kw in info.get("indication", "").lower() 
                   for kw in keywords):
                matching.append((drug, info))
        
        return matching
    
    async def _semantic_search(self, query: str) -> Dict[str, List]:
        """Perform semantic similarity search"""
        if not self.embeddings:
            return {"content": [], "sources": []}
        
        try:
            # In production: compute query embedding and search vector DB
            # For now, return empty (placeholder)
            logger.info("Semantic search would be performed here with real embeddings")
            return {"content": [], "sources": []}
        
        except Exception as e:
            logger.warning(f"Semantic search error: {str(e)}")
            return {"content": [], "sources": []}
    
    def get_stats(self) -> Dict:
        """Get RAG component statistics"""
        return {
            "knowledge_base_size": sum(
                len(self.knowledge_index.get(k, [])) 
                for k in ["guidelines", "protocols"]
            ) + len(self.knowledge_index.get("conditions", {})) + len(self.knowledge_index.get("drugs", {})),
            "total_retrievals": len(self.retrieval_stats),
            "average_results_per_query": (
                sum(s.get("results_count", 0) for s in self.retrieval_stats) / 
                max(len(self.retrieval_stats), 1)
            )
        }

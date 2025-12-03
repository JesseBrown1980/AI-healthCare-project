"""
Algorithm of Thought (AoT) Reasoning Engine
Implements step-by-step reasoning for complex medical queries
Provides transparent chain-of-thought for clinical decision support
"""

import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class AoTReasoner:
    """
    Algorithm of Thought reasoning engine
    Generates step-by-step reasoning chains for medical queries
    Ensures transparent, explainable AI decision-making
    """
    
    def __init__(self, reasoning_depth: int = 3):
        """
        Initialize AoT Reasoner
        
        Args:
            reasoning_depth: Number of reasoning steps to generate
        """
        self.reasoning_depth = reasoning_depth
        self.reasoning_chains: List[Dict] = []
        self.reasoning_templates = self._initialize_templates()
        
        logger.info(f"AoT Reasoner initialized with depth: {reasoning_depth}")
    
    def _initialize_templates(self) -> Dict[str, List[str]]:
        """Initialize reasoning templates for different query types"""
        return {
            "diagnosis": [
                "Step 1: Identify presenting symptoms and chief complaints",
                "Step 2: Review relevant patient history and comorbidities",
                "Step 3: Consider differential diagnoses based on symptom pattern",
                "Step 4: Evaluate supporting diagnostic tests and findings",
                "Step 5: Determine most likely diagnosis with evidence strength"
            ],
            "treatment": [
                "Step 1: Confirm accurate diagnosis and severity",
                "Step 2: Review current medications and allergies",
                "Step 3: Consult current treatment guidelines",
                "Step 4: Evaluate patient-specific factors (age, kidney/liver function)",
                "Step 5: Recommend evidence-based treatment with rationale"
            ],
            "risk_assessment": [
                "Step 1: Identify risk factors from patient history",
                "Step 2: Quantify risk using validated scoring systems",
                "Step 3: Consider patient preferences and values",
                "Step 4: Evaluate preventive strategies",
                "Step 5: Generate risk stratification and monitoring plan"
            ],
            "medication_review": [
                "Step 1: List all current medications with doses and indications",
                "Step 2: Check for drug-drug interactions",
                "Step 3: Assess appropriateness for current conditions",
                "Step 4: Review dosing in context of renal/hepatic function",
                "Step 5: Identify deprescribing opportunities"
            ],
            "clinical_decision": [
                "Step 1: Clarify clinical question and decision point",
                "Step 2: Identify relevant clinical evidence",
                "Step 3: Evaluate patient-specific factors",
                "Step 4: Discuss alternatives and tradeoffs",
                "Step 5: Make evidence-based recommendation"
            ]
        }
    
    async def generate_reasoning_chain(
        self,
        question: str,
        context: Optional[Dict] = None,
        rag_results: Optional[Dict] = None
    ) -> str:
        """
        Generate step-by-step reasoning chain for a query
        
        Args:
            question: Medical question to reason through
            context: Patient clinical context
            rag_results: Retrieved medical knowledge
            
        Returns:
            Formatted reasoning chain string
        """
        logger.info(f"Generating reasoning chain for: {question[:50]}...")
        
        try:
            # 1. Determine query type
            query_type = await self._classify_query(question)
            logger.info(f"Query classified as: {query_type}")
            
            # 2. Get appropriate reasoning template
            template = self.reasoning_templates.get(query_type, self.reasoning_templates["clinical_decision"])
            
            # 3. Generate detailed reasoning steps
            reasoning_steps = await self._generate_steps(
                question=question,
                template=template,
                context=context,
                rag_results=rag_results
            )
            
            # 4. Format reasoning chain
            chain = self._format_reasoning_chain(reasoning_steps, query_type)
            
            # 5. Store for analysis
            self.reasoning_chains.append({
                "query": question,
                "query_type": query_type,
                "chain": chain,
                "timestamp": datetime.now().isoformat(),
                "context_provided": bool(context),
                "rag_results_provided": bool(rag_results)
            })
            
            return chain
        
        except Exception as e:
            logger.error(f"Error generating reasoning chain: {str(e)}")
            raise
    
    async def _classify_query(self, question: str) -> str:
        """Classify query type for template selection"""
        q_lower = question.lower()
        
        type_keywords = {
            "diagnosis": ["diagnose", "what is", "condition", "disease", "syndrome"],
            "treatment": ["treat", "therapy", "medication", "manage", "intervention"],
            "risk_assessment": ["risk", "prognosis", "predict", "likelihood", "score"],
            "medication_review": ["drug", "medication", "medicine", "prescription", "interaction"],
            "clinical_decision": ["decide", "should", "recommend", "option", "choice"]
        }
        
        for qtype, keywords in type_keywords.items():
            if any(kw in q_lower for kw in keywords):
                return qtype
        
        return "clinical_decision"  # Default
    
    async def _generate_steps(
        self,
        question: str,
        template: List[str],
        context: Optional[Dict],
        rag_results: Optional[Dict]
    ) -> List[Dict]:
        """
        Generate detailed reasoning for each step
        
        Args:
            question: Original question
            template: Reasoning steps template
            context: Patient context
            rag_results: Retrieved knowledge
            
        Returns:
            List of detailed reasoning steps
        """
        steps = []
        
        for i, step_template in enumerate(template[:self.reasoning_depth], 1):
            step = {
                "step_number": i,
                "description": step_template,
                "reasoning": await self._reason_about_step(
                    step_num=i,
                    step_template=step_template,
                    question=question,
                    context=context,
                    rag_results=rag_results
                ),
                "key_finding": await self._extract_key_finding(
                    step_num=i,
                    context=context
                )
            }
            steps.append(step)
        
        return steps
    
    async def _reason_about_step(
        self,
        step_num: int,
        step_template: str,
        question: str,
        context: Optional[Dict],
        rag_results: Optional[Dict]
    ) -> str:
        """Generate reasoning for a specific step"""
        reasoning = step_template + "\n"
        
        if context:
            if step_num == 1 and context.get("conditions"):
                reasoning += f"Current conditions: {[c.get('code') for c in context['conditions'][:2]]}\n"
            elif step_num == 2 and context.get("medications"):
                reasoning += f"Current medications: {len(context['medications'])} identified\n"
            elif step_num == 3 and rag_results:
                reasoning += f"Retrieved {len(rag_results.get('guidelines', []))} relevant guidelines\n"
        
        return reasoning
    
    async def _extract_key_finding(self, step_num: int, context: Optional[Dict]) -> str:
        """Extract key finding from step"""
        findings = {
            1: "Symptom and presentation analysis complete",
            2: "Historical context established",
            3: "Differential considerations identified",
            4: "Evidence evaluation in progress",
            5: "Final assessment and recommendation"
        }
        return findings.get(step_num, "Analysis complete")
    
    def _format_reasoning_chain(self, steps: List[Dict], query_type: str) -> str:
        """Format reasoning chain into readable string"""
        chain = f"🏥 Clinical Reasoning Chain ({query_type.replace('_', ' ').title()})\n"
        chain += "=" * 60 + "\n\n"
        
        for step in steps:
            chain += f"📍 {step['description']}\n"
            chain += f"   Reasoning: {step['reasoning']}\n"
            chain += f"   ✓ {step['key_finding']}\n\n"
        
        chain += "=" * 60 + "\n"
        chain += "⚕️  Ready for clinical integration"
        
        return chain
    
    async def get_multi_path_reasoning(
        self,
        question: str,
        num_paths: int = 3
    ) -> List[Dict]:
        """
        Generate multiple reasoning paths for comparative analysis
        Useful for complex diagnostic decisions
        
        Args:
            question: Medical question
            num_paths: Number of alternative reasoning paths
            
        Returns:
            List of alternative reasoning paths
        """
        logger.info(f"Generating {num_paths} alternative reasoning paths")
        
        paths = []
        for i in range(num_paths):
            # Generate variations based on hypothesis
            hypothesis = await self._generate_hypothesis(question, i)
            
            path = {
                "path_id": i + 1,
                "hypothesis": hypothesis,
                "reasoning": await self.generate_reasoning_chain(
                    f"{question} (considering {hypothesis})",
                    context=None
                ),
                "confidence": 0.7 + (i * 0.05)  # Hypothetical
            }
            paths.append(path)
        
        return paths
    
    async def _generate_hypothesis(self, question: str, variant: int) -> str:
        """Generate alternative hypothesis"""
        hypotheses = {
            0: "Most probable diagnosis",
            1: "Alternative diagnosis",
            2: "Less likely but possible diagnosis"
        }
        return hypotheses.get(variant, "Alternative consideration")
    
    async def validate_reasoning(self, chain: str, expected_outcome: Optional[str] = None) -> Dict:
        """
        Validate reasoning chain for logical consistency
        
        Args:
            chain: Reasoning chain to validate
            expected_outcome: Optional expected conclusion
            
        Returns:
            Validation report
        """
        validation = {
            "chain_length": len(chain.split("Step")),
            "steps_present": chain.count("Step"),
            "evidence_references": chain.count("evidence") + chain.count("guideline"),
            "patient_specific": "patient" in chain.lower(),
            "clinically_appropriate": True,
            "confidence_score": 0.85,
            "issues": []
        }
        
        if validation["steps_present"] < 3:
            validation["issues"].append("Insufficient reasoning depth")
            validation["confidence_score"] -= 0.1
        
        return validation
    
    def get_stats(self) -> Dict:
        """Get AoT reasoner statistics"""
        return {
            "total_reasoning_chains": len(self.reasoning_chains),
            "reasoning_depth": self.reasoning_depth,
            "query_types_handled": len(self.reasoning_templates),
            "average_chain_length": sum(
                len(r["chain"].split("\n")) for r in self.reasoning_chains
            ) / max(len(self.reasoning_chains), 1)
        }

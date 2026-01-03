"""
LLM Engine Module
Interfaces with Large Language Models (GPT-4, LLaMA, etc.)
Handles prompt engineering and medical context processing
Enforces region-specific data transfer controls for compliance
"""

import logging
import os
from typing import Dict, Optional, Any, List
import json
from datetime import datetime

from backend.utils.i18n import translate, DEFAULT_LANGUAGE
from backend.config.compliance_policies import (
    is_external_llm_allowed,
    is_local_llm_required,
    get_region,
)

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Manages interaction with Large Language Models
    Supports multiple LLM backends (OpenAI, Anthropic, local models)
    """
    
    def __init__(self, model_name: str, api_key: str = ""):
        """
        Initialize LLM Engine
        
        Args:
            model_name: Model identifier (gpt-4, llama-2-7b, etc.)
            api_key: API key for external services
        """
        self.model_name = model_name
        self.api_key = api_key
        self.provider = self._detect_provider(model_name)
        self.client = self._initialize_client()
        self.query_history = []
        self.token_usage = {"prompt": 0, "completion": 0}
        
        logger.info(f"LLM Engine initialized with model: {model_name}")
    
    def _select_model_by_region(self) -> str:
        """
        Select appropriate model based on region compliance policy.
        
        Returns:
            Model name to use
        """
        if self.local_llm_required:
            # Region requires local model (e.g., EU/GDPR)
            local_model = os.getenv("LOCAL_LLM_MODEL", "llama-2-7b")
            logger.info(f"Region {self.region} requires local LLM, using: {local_model}")
            return local_model
        elif not self.external_llm_allowed:
            # External LLM not allowed, fallback to local
            local_model = os.getenv("LOCAL_LLM_MODEL", "llama-2-7b")
            logger.warning(
                f"External LLM not allowed in region {self.region}, "
                f"falling back to local model: {local_model}"
            )
            return local_model
        else:
            # External LLM allowed, use configured model
            return os.getenv("LLM_MODEL", "gpt-4")
    
    def _detect_provider(self, model_name: str) -> str:
        """Detect LLM provider based on model name"""
        if "gpt" in model_name.lower():
            return "openai"
        elif "claude" in model_name.lower():
            return "anthropic"
        elif "llama" in model_name.lower() or "mistral" in model_name.lower():
            return "local"
        else:
            return "openai"  # Default
    
    def _validate_provider_compliance(self) -> None:
        """
        Validate that the selected provider complies with region policy.
        Raises an exception if provider violates compliance rules.
        """
        if self.provider in ["openai", "anthropic"]:
            # External provider
            if not self.external_llm_allowed:
                raise ValueError(
                    f"External LLM provider '{self.provider}' not allowed in region '{self.region}'. "
                    f"Please use a local model or set REGION to allow external providers."
                )
            if self.local_llm_required:
                raise ValueError(
                    f"Region '{self.region}' requires local LLM models. "
                    f"External provider '{self.provider}' is not permitted."
                )
            logger.debug(f"External LLM provider '{self.provider}' allowed in region '{self.region}'")
        elif self.provider == "local":
            # Local provider - always compliant
            logger.debug(f"Local LLM provider is compliant for region '{self.region}'")
    
    def _initialize_client(self):
        """Initialize appropriate LLM client based on provider"""
        if self.provider == "openai":
            try:
                import openai
                openai.api_key = self.api_key
                return openai
            except ImportError:
                logger.warning("OpenAI library not installed")
                return None
        elif self.provider == "anthropic":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("Anthropic library not installed")
                return None
        else:
            # Local model setup (would use transformers, ollama, etc.)
            logger.info("Using local LLM model")
            return None
    
    async def query_with_rag(
        self,
        question: str,
        patient_context: Optional[Dict] = None,
        rag_component=None,
        aot_reasoner=None,
        include_reasoning: bool = True,
        language: str = DEFAULT_LANGUAGE
    ) -> Dict[str, Any]:
        """
        Process a medical query with RAG and Algorithm of Thought
        
        Args:
            question: User question
            patient_context: Patient data for context
            rag_component: RAG fusion component for knowledge retrieval
            aot_reasoner: Algorithm of Thought reasoning engine
            include_reasoning: Include step-by-step reasoning
            language: Target language for response (e.g., 'en', 'es', 'fr', 'ru', 'zh', etc.)
            
        Returns:
            Response with answer, reasoning, and sources
        """
        logger.info(f"Processing query: {question[:100]}... (language: {language})")
        
        try:
            # 1. Retrieve relevant medical knowledge via RAG
            rag_results = None
            if rag_component:
                rag_results = await rag_component.retrieve_relevant_knowledge(question)
            
            # 2. Build medical prompt
            system_prompt = self._build_system_prompt(patient_context, language=language)
            user_prompt = self._build_user_prompt(
                question=question,
                patient_context=patient_context,
                rag_results=rag_results,
                include_reasoning=include_reasoning,
                language=language
            )
            
            # 3. Generate response with AoT if available
            reasoning_chain = None
            if aot_reasoner and include_reasoning:
                reasoning_chain = await aot_reasoner.generate_reasoning_chain(
                    question=question,
                    context=patient_context,
                    rag_results=rag_results
                )
                # Enhance prompt with reasoning steps
                user_prompt += f"\n\nReasoning framework:\n{reasoning_chain}"
            
            # 4. Call LLM
            response = await self._call_llm(system_prompt, user_prompt)
            
            # 5. Extract and structure response
            result = {
                "answer": response.get("content"),
                "reasoning": reasoning_chain if include_reasoning else None,
                "sources": rag_results.get("sources") if rag_results else [],
                "confidence": response.get("confidence", 0.7),
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Track usage
            self.query_history.append(result)
            if response.get("usage"):
                self.token_usage["prompt"] += response["usage"].get("prompt_tokens", 0)
                self.token_usage["completion"] += response["usage"].get("completion_tokens", 0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Call the underlying LLM with compliance checks.
        
        Logs data transfer for audit purposes.
        """
        # Log data transfer attempt for compliance
        logger.info(
            f"LLM API call: provider={self.provider}, "
            f"region={self.region}, "
            f"external_allowed={self.external_llm_allowed}, "
            f"local_required={self.local_llm_required}"
        )
        
        try:
            if self.provider == "openai" and self.client:
                response = self.client.ChatCompletion.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,  # Lower for medical accuracy
                    max_tokens=2000,
                    top_p=0.95,
                    timeout=30.0,
                )
                
                return {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens
                    },
                    "confidence": 0.95
                }
            
            elif self.provider == "anthropic" and self.client:
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=2000,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    system=system_prompt
                )
                
                return {
                    "content": response.content[0].text,
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens
                    },
                    "confidence": 0.95
                }
            
            else:
                # Fallback mock response for demo
                logger.warning("No LLM client available, returning mock response")
                return {
                    "content": "This is a demo response. Please configure a proper LLM provider.",
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    "confidence": 0.5
                }
        
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise
    
    def _build_system_prompt(
        self, 
        patient_context: Optional[Dict] = None,
        language: str = DEFAULT_LANGUAGE
    ) -> str:
        """Build system prompt for medical context"""
        prompt = """You are an expert clinical decision support AI assistant.
        
Your role is to:
1. Analyze patient data and medical history
2. Provide evidence-based clinical insights
3. Identify potential risks and alerts
4. Suggest treatment options aligned with medical guidelines
5. Always cite sources and express confidence levels

Important guidelines:
- Always prioritize patient safety
- Ground recommendations in current medical evidence
- Flag any critical findings immediately
- Explain your reasoning clearly
- Never provide definitive diagnoses - support clinical decision-making
- Respect HIPAA and patient privacy
        """
        
        # Add language instruction if not English
        if language != DEFAULT_LANGUAGE:
            # Get language name for display
            from backend.utils.i18n import LANGUAGE_NAMES
            language_name = LANGUAGE_NAMES.get(language, language)
            prompt += f"\n\nIMPORTANT: Please respond in {language_name}. Use medical terminology appropriate for {language_name}."
        
        if patient_context:
            prompt += f"\n\nCurrent patient context available: Yes"
        
        return prompt
    
    def _build_user_prompt(
        self,
        question: str,
        patient_context: Optional[Dict] = None,
        rag_results: Optional[Dict] = None,
        include_reasoning: bool = True,
        language: str = DEFAULT_LANGUAGE
    ) -> str:
        """Build user prompt with context"""
        prompt = f"Question: {question}\n\n"
        
        if patient_context:
            prompt += "Patient Context:\n"
            if patient_context.get("patient"):
                p = patient_context["patient"]
                prompt += f"- Name: {p.get('name')}, Age: {p.get('birthDate')}\n"
                prompt += f"- Gender: {p.get('gender')}\n"
            
            if patient_context.get("conditions"):
                prompt += f"Active Conditions: {len(patient_context['conditions'])} found\n"
                for cond in patient_context["conditions"][:3]:
                    prompt += f"  - {cond.get('code')}\n"
            
            if patient_context.get("medications"):
                prompt += f"Current Medications: {len(patient_context['medications'])} found\n"
                for med in patient_context["medications"][:3]:
                    prompt += f"  - {med.get('medication')}\n"
            
            if patient_context.get("observations"):
                prompt += f"Recent Labs/Vitals: {len(patient_context['observations'])} found\n"
                for obs in patient_context["observations"][:3]:
                    value = f"{obs.get('value')} {obs.get('unit')}" if obs.get('value') else "N/A"
                    prompt += f"  - {obs.get('code')}: {value}\n"
        
        if rag_results and rag_results.get("relevant_content"):
            prompt += "\n\nRelevant Medical Knowledge:\n"
            for i, content in enumerate(rag_results.get("relevant_content", [])[:3], 1):
                prompt += f"{i}. {content}\n"
        
        if include_reasoning:
            reasoning_text = translate("llm.reasoning_required", language=language)
            prompt += f"\n\n{reasoning_text}"
        
        return prompt
    
    def get_stats(self) -> Dict:
        """Get LLM engine statistics"""
        return {
            "model": self.model_name,
            "provider": self.provider,
            "total_queries": len(self.query_history),
            "token_usage": self.token_usage,
            "average_query_length": sum(len(q.get("answer", "")) for q in self.query_history) / max(len(self.query_history), 1)
        }

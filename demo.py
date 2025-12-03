#!/usr/bin/env python3
"""
Healthcare AI Assistant - Quick Demo Script

This script demonstrates how to use the Healthcare AI system programmatically.
It shows a simple example of patient analysis with mocked components.

Usage:
    python demo.py
"""

import asyncio
import json
from pathlib import Path

# Import backend modules
from backend.patient_analyzer import PatientAnalyzer
from backend.fhir_connector import FHIRConnector
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.s_lora_manager import SLoRAManager
from backend.aot_reasoner import AoTReasoner
from backend.mlc_learning import MLCLearning


def load_sample_patient():
    """Load sample patient JSON from test data"""
    path = Path(__file__).parent / "tests" / "data" / "sample_patient.json"
    with open(path) as f:
        return json.load(f)


async def main():
    """Run a simple patient analysis demo"""
    
    print("🏥 Healthcare AI Assistant - Demo")
    print("=" * 60)
    
    # Initialize components
    print("\n📦 Initializing components...")
    fhir = FHIRConnector(server_url="http://localhost:8080/fhir")
    llm = LLMEngine(model_name="gpt-4", api_key="demo-key")
    rag = RAGFusion(knowledge_base_path="./data/medical_kb")
    slora = SLoRAManager(adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf")
    aot = AoTReasoner()
    mlc = MLCLearning(learning_rate=0.01)
    print("✅ Components initialized")
    
    # Create analyzer
    print("\n🔧 Creating analyzer...")
    analyzer = PatientAnalyzer(
        fhir_connector=fhir,
        llm_engine=llm,
        rag_fusion=rag,
        s_lora_manager=slora,
        aot_reasoner=aot,
        mlc_learning=mlc
    )
    print("✅ Analyzer ready")
    
    # Load sample patient
    print("\n📋 Loading sample patient data...")
    patient = load_sample_patient()
    print(f"✅ Loaded patient: {patient.get('name', ['Unknown'])[0].get('given', [''])}")
    print(f"   ID: {patient.get('id')}")
    print(f"   Gender: {patient.get('gender', 'Unknown')}")
    print(f"   DOB: {patient.get('birthDate', 'Unknown')}")
    
    # Display component stats
    print("\n📊 System Status:")
    print(f"   FHIR Server: {fhir.get_stats()['server']}")
    print(f"   LLM Provider: {llm.provider}")
    print(f"   Model: {llm.model_name}")
    print(f"   Available Adapters: {len(slora.adapters)}")
    print(f"   MLC Learning Rate: {mlc.learning_rate}")
    
    # Show component capabilities
    print("\n🎯 Available Features:")
    print("   ✓ FHIR data integration")
    print("   ✓ Multi-provider LLM support (OpenAI, Anthropic, local)")
    print("   ✓ RAG-Fusion knowledge retrieval")
    print("   ✓ S-LoRA specialty adapters (10+ specialties)")
    print("   ✓ Algorithm of Thought reasoning")
    print("   ✓ Meta-Learning for continuous improvement")
    
    # Example query
    print("\n💡 Example Usage:")
    print("   from backend.patient_analyzer import PatientAnalyzer")
    print("   ...")
    print("   analysis = await analyzer.analyze(")
    print('       patient_id="patient-123",')
    print('       include_recommendations=True,')
    print('       specialty="cardiology"')
    print("   )")
    print("   print(analysis['summary'])")
    print("   print(analysis['alerts'])")
    print("   print(analysis['recommendations'])")
    
    # Run tests info
    print("\n🧪 Testing:")
    print("   Run full test suite:     pytest -q")
    print("   Run specific tests:      pytest tests/test_fhir_connector.py -v")
    print("   Run with coverage:       pytest --cov=backend tests/")
    
    print("\n📚 Documentation:")
    print("   Getting Started:  GETTING_STARTED.md")
    print("   Installation:     INSTALL.md")
    print("   API Reference:    README.md")
    print("   Quick Ref:        QUICK_REFERENCE.md")
    
    print("\n🚀 Next Steps:")
    print("   1. Configure .env with your API keys")
    print("   2. Connect to FHIR server")
    print("   3. Run: docker-compose up")
    print("   4. Open: http://localhost:3000")
    
    print("\n" + "=" * 60)
    print("✨ Demo complete! See documentation for full API usage.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you're in the project root directory:")
        print("  cd /path/to/AI-healthCare-project")
        print("  python demo.py")

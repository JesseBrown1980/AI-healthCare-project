
import asyncio
import torch
# Add the project root to sys.path so we can import from backend
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.anomaly_detector.service import anomaly_service
from backend.anomaly_detector.models.schemas import LogEvent
from backend.anomaly_detector.models.graph_builder import GraphBuilder
from datetime import datetime

async def test_flow():
    print("--- Starting GNN Anomaly Service Verification ---")
    
    # 1. Initialize Service
    print("[1] Initializing Service...")
    anomaly_service.initialize()
    model = anomaly_service.get_model()
    
    if model is None:
        print("❌ Model failed to initialize.")
        return
    print("✅ Model initialized.")

    # 2. Simulate Data
    print("[2] Simulating Audit Logs...")
    events = [
        LogEvent(
            event_id="evt_1",
            timestamp=datetime.utcnow(),
            source_entity="user_123",
            destination_entity="patient_record_abc",
            action="READ"
        ),
        LogEvent(
            event_id="evt_2",
            timestamp=datetime.utcnow(),
            source_entity="user_123",
            destination_entity="system_config",
            action="DELETE" # Suspicious
        )
    ]
    
    # 3. Build Graph
    print("[3] Building Graph from Events...")
    builder = GraphBuilder(feature_dim=16)
    x, edge_index, event_ids = builder.build_graph(events)
    print(f"   Nodes: {x.shape[0]}, Edges: {edge_index.shape[1]}")
    
    # 4. Inference
    print("[4] Running Inference...")
    model.eval()
    with torch.no_grad():
        scores = model(x, edge_index)
        print(f"   Raw Scores: {scores}")
        
    print("✅ Verification Complete. Flow works end-to-end.")

if __name__ == "__main__":
    asyncio.run(test_flow())

import pytest
import os
from unittest.mock import MagicMock, AsyncMock
from backend.agent_manager import AgentManager
from backend.notifier import Notifier
from tests.conftest_integration import real_llm_engine

@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_manager_real_world_simulation(real_llm_engine):
    """
    Tests the Agent Manager in a 'Staging' like environment.
    Uses either real OpenAI (if key env var set) or high-fidelity mock.
    """
    agent = AgentManager(llm_engine=real_llm_engine)
    
    # 1. Test Safe Notification
    safe_payload = {
        "notification_type": "system_status",
        "body": "System maintenance scheduled for 2 AM."
    }
    decision = await agent.review_notification(safe_payload)
    assert decision["action"] == "APPROVE", f"Expected APPROVE, got {decision}"
    print(f"\n[PASS] Safe Message Review: {decision['reason']}")

    # 2. Test PHI Leak (The "John Doe has Cancer" scenario)
    phi_payload = {
        "notification_type": "alert",
        "patient_id": "12345",
        "body": "Urgent: Patient John Doe diagnosed with Stage 4 Cancer."
    }
    decision = await agent.review_notification(phi_payload)
    assert decision["action"] == "REJECT", f"Expected REJECT, got {decision}"
    assert "PHI" in decision["reason"] or "Sensitive" in decision["reason"]
    print(f"[PASS] PHI Leak Blocked: {decision['reason']}")

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_system_flow(real_llm_engine):
    """
    Tests the entire flow Notifier -> Agent -> LLM.
    """
    agent = AgentManager(llm_engine=real_llm_engine)
    notifier = Notifier(channels=[], agent_manager=agent)
    
    # Mock channel to verify call
    mock_channel = MagicMock()
    mock_channel.notify = AsyncMock(return_value={"status": "sent"})
    notifier.channels = [mock_channel]
    
    # Flow 1: Safe Message -> Should Send
    await notifier.notify({"body": "Hello World"})
    mock_channel.notify.assert_called() 
    print("[PASS] Full System Flow: Safe message delivered.")
    
    mock_channel.reset_mock()
    
    # Flow 2: Unsafe Message -> Should NOT Send
    result = await notifier.notify({"body": "User password is 'secret123'"})
    mock_channel.notify.assert_not_called()
    assert result["status"] == "rejected"
    print("[PASS] Full System Flow: Unsafe message intercepted.")

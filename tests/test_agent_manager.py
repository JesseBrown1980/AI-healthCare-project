import pytest
import logging
from unittest.mock import AsyncMock, MagicMock
from backend.agent_manager import AgentManager
from backend.notifier import Notifier
from backend.llm_engine import LLMEngine

# Test Agent Manager
@pytest.mark.asyncio
async def test_agent_manager_review_approve():
    mock_llm = MagicMock(spec=LLMEngine)
    mock_llm.query_generic = AsyncMock(return_value={"content": '{"action": "APPROVE", "reason": "Safe"}'})
    
    manager = AgentManager(llm_engine=mock_llm)
    payload = {"patient_id": "123", "body": "Routine checkup"}
    
    decision = await manager.review_notification(payload)
    assert decision["action"] == "APPROVE"
    assert decision["reason"] == "Safe"

@pytest.mark.asyncio
async def test_agent_manager_review_reject():
    mock_llm = MagicMock(spec=LLMEngine)
    mock_llm.query_generic = AsyncMock(return_value={"content": '{"action": "REJECT", "reason": "PHI Leak"}'})
    
    manager = AgentManager(llm_engine=mock_llm)
    payload = {"patient_id": "123", "body": "Patient John Doe has Cancer"}
    
    decision = await manager.review_notification(payload)
    assert decision["action"] == "REJECT"
    assert "PHI Leak" in decision["reason"]

@pytest.mark.asyncio
async def test_agent_manager_review_malformed_json_fallback():
    mock_llm = MagicMock(spec=LLMEngine)
    # LLM returns junk non-JSON
    mock_llm.query_generic = AsyncMock(return_value={"content": 'I think this is okay but I am not JSON'})
    
    manager = AgentManager(llm_engine=mock_llm)
    payload = {"body": "test"}
    
    decision = await manager.review_notification(payload)
    # Fallback open
    assert decision["action"] == "APPROVE" 
    assert "JSON parse error" in decision["reason"] or "LLM output format unclear" in decision["reason"]

# Test Notifier Integration
@pytest.mark.asyncio
async def test_notifier_with_agent_manager_approve():
    mock_agent = MagicMock(spec=AgentManager)
    mock_agent.review_notification = AsyncMock(return_value={"action": "APPROVE", "reason": "Go ahead"})
    
    mock_channel = MagicMock()
    mock_channel.notify = AsyncMock(return_value={"status": "sent"})
    
    notifier = Notifier(channels=[mock_channel], agent_manager=mock_agent)
    
    result = await notifier.notify({"msg": "hello"})
    
    # Should call agent review
    mock_agent.review_notification.assert_called_once()
    # Should call channel notify
    mock_channel.notify.assert_called_once()
    
@pytest.mark.asyncio
async def test_notifier_with_agent_manager_reject():
    mock_agent = MagicMock(spec=AgentManager)
    mock_agent.review_notification = AsyncMock(return_value={"action": "REJECT", "reason": "Blocked"})
    
    mock_channel = MagicMock()
    mock_channel.notify = AsyncMock(return_value={"status": "sent"})
    
    notifier = Notifier(channels=[mock_channel], agent_manager=mock_agent)
    
    result = await notifier.notify({"msg": "bad msg"})
    
    # Should call agent review
    mock_agent.review_notification.assert_called_once()
    # Should NOT call channel notify
    mock_channel.notify.assert_not_called()
    
    assert result["status"] == "rejected"
    assert result["reason"] == "Blocked"

@pytest.mark.asyncio
async def test_notifier_no_agent_manager():
    mock_channel = MagicMock()
    mock_channel.notify = AsyncMock(return_value={"status": "sent"})
    
    notifier = Notifier(channels=[mock_channel]) # No agent manager
    
    await notifier.notify({"msg": "hello"})
    
    mock_channel.notify.assert_called_once()

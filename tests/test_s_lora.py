import asyncio
from backend.s_lora_manager import SLoRAManager


def test_initialize_adapters():
    mgr = SLoRAManager(adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf")
    assert len(mgr.adapters) >= 5
    assert "adapter_cardiology" in mgr.adapters.values().__str__() or "adapter_cardiology" in mgr.adapters


def test_select_adapters_simple():
    mgr = SLoRAManager(adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf")
    selected = asyncio.run(mgr.select_adapters(["cardiology"]))
    assert isinstance(selected, list)
    assert any("cardio" in a for a in selected)


def test_activate_deactivate_adapter():
    mgr = SLoRAManager(adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf")
    adapter = list(mgr.adapters.keys())[0]
    ok = asyncio.run(mgr.activate_adapter(adapter))
    assert ok is True
    # Deactivate
    ok2 = asyncio.run(mgr.deactivate_adapter(adapter))
    assert ok2 is True

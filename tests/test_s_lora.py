"""Behavioral checks for the Sparse LoRA manager helpers."""

import asyncio

import pytest

from backend.s_lora_manager import SLoRAManager


ADAPTER_PATH = "./models/adapters"
BASE_MODEL = "meta-llama/Llama-2-7b-hf"


@pytest.fixture
def slo_ra_manager() -> SLoRAManager:
    """Provide a fresh manager per test to keep lifecycle isolation."""

    return SLoRAManager(adapter_path=ADAPTER_PATH, base_model=BASE_MODEL)

def test_activate_deactivate_adapter():
    mgr = SLoRAManager(adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf")
    adapter = list(mgr.adapters.keys())[0]
    ok = asyncio.run(mgr.activate_adapter(adapter))
    assert ok is True
    # Deactivate
    ok2 = asyncio.run(mgr.deactivate_adapter(adapter))
    assert ok2 is True

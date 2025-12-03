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


def test_initialize_adapters(slo_ra_manager: SLoRAManager):
    """Manager should bootstrap all specialties with readable names."""

    assert len(slo_ra_manager.adapters) == 10
    assert "adapter_cardiology" in slo_ra_manager.adapters
    status = asyncio.run(slo_ra_manager.get_status())
    assert "adapter_cardiology" in status["available"]
    assert slo_ra_manager.base_model == BASE_MODEL


def test_select_adapters_simple(slo_ra_manager: SLoRAManager):
    """Selecting by specialty returns appropriately prefixed adapter names."""

    selected = asyncio.run(
        slo_ra_manager.select_adapters(["cardiology", "neurology"])
    )
    assert isinstance(selected, list)
    assert {"adapter_cardiology", "adapter_neurology"}.issubset(selected)
    assert all(name.startswith("adapter_") for name in selected)


def test_activate_deactivate_adapter(slo_ra_manager: SLoRAManager):
    """Lifecycle operations flip adapter status and membership sets."""

    adapter = next(iter(slo_ra_manager.adapters))

    ok_activate = asyncio.run(slo_ra_manager.activate_adapter(adapter))
    assert ok_activate is True
    assert adapter in slo_ra_manager.active_adapters
    assert slo_ra_manager.adapters[adapter]["status"] == "active"

    ok_deactivate = asyncio.run(slo_ra_manager.deactivate_adapter(adapter))
    assert ok_deactivate is True
    assert adapter not in slo_ra_manager.active_adapters
    assert slo_ra_manager.adapters[adapter]["status"] == "available"

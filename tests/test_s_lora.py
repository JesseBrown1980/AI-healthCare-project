"""Tests for the SLoRAManager adapter lifecycle helpers."""

import asyncio

import pytest

from backend.s_lora_manager import SLoRAManager


@pytest.fixture
def slo_ra_manager():
    """Provide a fresh manager instance for each test."""

    return SLoRAManager(
        adapter_path="./models/adapters", base_model="meta-llama/Llama-2-7b-hf"
    )


def test_initialize_adapters(slo_ra_manager):
    assert len(slo_ra_manager.adapters) >= 5
    assert (
        "adapter_cardiology" in slo_ra_manager.adapters.values().__str__()
        or "adapter_cardiology" in slo_ra_manager.adapters
    )


def test_select_adapters_simple(slo_ra_manager):
    selected = asyncio.run(slo_ra_manager.select_adapters(["cardiology"]))
    assert isinstance(selected, list)
    assert any("cardio" in a for a in selected)


def test_activate_deactivate_adapter(slo_ra_manager):
    adapter = list(slo_ra_manager.adapters.keys())[0]
    ok = asyncio.run(slo_ra_manager.activate_adapter(adapter))
    assert ok is True
    # Deactivate
    ok2 = asyncio.run(slo_ra_manager.deactivate_adapter(adapter))
    assert ok2 is True

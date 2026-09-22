"""Integration setup tests."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry
from salus_it600.exceptions import IT600ConnectionError

import custom_components.salus as salus_init
from custom_components.salus import PLATFORMS, async_setup_entry
from custom_components.salus.const import CONF_SCAN_INTERVAL, DOMAIN


class FakeGateway:
    """Gateway fake for setup tests."""

    instances: list[FakeGateway] = []
    poll_error: Exception | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.closed = False
        FakeGateway.instances.append(self)

    async def connect(self) -> str:
        return "gateway-1"

    async def poll_status(self) -> None:
        if FakeGateway.poll_error is not None:
            raise FakeGateway.poll_error

    async def close(self) -> None:
        self.closed = True

    def get_gateway_device(self) -> SimpleNamespace:
        return SimpleNamespace(
            unique_id="gateway-1",
            manufacturer="SALUS",
            name="Gateway",
            model="UGE600",
            sw_version="1.0",
        )

    def get_climate_devices(self) -> dict[str, Any]:
        return {}

    def get_binary_sensor_devices(self) -> dict[str, Any]:
        return {}

    def get_switch_devices(self) -> dict[str, Any]:
        return {}

    def get_cover_devices(self) -> dict[str, Any]:
        return {}

    def get_sensor_devices(self) -> dict[str, Any]:
        return {}


@pytest.fixture(autouse=True)
def reset_fake_gateway():
    FakeGateway.instances = []
    FakeGateway.poll_error = None


async def test_setup_entry_forwards_platforms(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})

    with (
        patch.object(salus_init, "IT600Gateway", FakeGateway),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as mock_forward,
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_forward.assert_called_once_with(entry, PLATFORMS)
    assert FakeGateway.instances[0].kwargs[CONF_HOST] == "192.0.2.10"
    assert FakeGateway.instances[0].kwargs["session"] is not None
    assert not FakeGateway.instances[0].closed


async def test_setup_entry_uses_configured_scan_interval(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
        options={CONF_SCAN_INTERVAL: 45},
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})

    with (
        patch.object(salus_init, "IT600Gateway", FakeGateway),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=45)


async def test_failed_setup_closes_gateway_and_clears_runtime_data(
    hass: HomeAssistant,
) -> None:
    """A failed first refresh must not leave a half-initialized entry behind."""
    FakeGateway.poll_error = IT600ConnectionError("gateway unreachable")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    entry.add_to_hass(hass)

    with (
        patch.object(salus_init, "IT600Gateway", FakeGateway),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)

    assert FakeGateway.instances[0].closed is True
    assert not hasattr(entry, "runtime_data")


async def test_unload_entry_closes_gateway_and_cancels_pending_refresh(
    hass: HomeAssistant,
) -> None:
    """Unloading must release the gateway and leave no refresh task behind."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
    )
    entry.add_to_hass(hass)

    with patch.object(salus_init, "IT600Gateway", FakeGateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = entry.runtime_data.coordinator
        gateway = FakeGateway.instances[0]
        await coordinator.async_request_debounced_refresh()
        assert coordinator._debounced_refresh_task is not None
        assert gateway.closed is False

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert gateway.closed is True
    assert coordinator._debounced_refresh_task is None
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_changing_options_reloads_the_entry(hass: HomeAssistant) -> None:
    """Options feed the coordinator at construction, so they need a reload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
        options={CONF_SCAN_INTERVAL: 20},
    )
    entry.add_to_hass(hass)

    with patch.object(salus_init, "IT600Gateway", FakeGateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        hass.config_entries.async_update_entry(entry, options={CONF_SCAN_INTERVAL: 45})
        await hass.async_block_till_done()

        assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=45)

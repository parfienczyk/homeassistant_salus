"""End-to-end tests driving the integration through Home Assistant services.

The rest of the suite calls entity methods directly, which bypasses the
service layer. These tests go through `hass.services.async_call` so the
debounce behaviour is exercised the way the frontend triggers it.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.salus as salus_init
from custom_components.salus.const import DOMAIN
from tests.conftest import make_climate_device

CLIMATE_ENTITY_ID = "climate.thermostat"


class ServiceGateway:
    """Gateway fake that records the writes a service call produces."""

    instances: list[ServiceGateway] = []

    def __init__(self, **kwargs: Any) -> None:
        self.device = make_climate_device(
            unique_id="climate-1",
            name="Thermostat",
        )
        self.temperature_writes: list[float] = []
        ServiceGateway.instances.append(self)

    async def connect(self) -> str:
        return "gateway-1"

    async def poll_status(self) -> None:
        return None

    async def close(self) -> None:
        return None

    def get_gateway_device(self) -> SimpleNamespace:
        return SimpleNamespace(
            unique_id="gateway-1",
            manufacturer="SALUS",
            name="Gateway",
            model="UGE600",
            sw_version="1.0",
        )

    def get_climate_devices(self) -> dict[str, Any]:
        return {self.device.unique_id: self.device}

    def get_binary_sensor_devices(self) -> dict[str, Any]:
        return {}

    def get_switch_devices(self) -> dict[str, Any]:
        return {}

    def get_cover_devices(self) -> dict[str, Any]:
        return {}

    def get_sensor_devices(self) -> dict[str, Any]:
        return {}

    async def set_climate_device_temperature(
        self,
        device_id: str,
        temperature: float,
    ) -> None:
        self.temperature_writes.append(temperature)


async def _setup(hass: HomeAssistant) -> ServiceGateway:
    ServiceGateway.instances = []
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.10", CONF_TOKEN: "001E5E0D32906128"},
    )
    entry.add_to_hass(hass)

    with patch.object(salus_init, "IT600Gateway", ServiceGateway):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get(CLIMATE_ENTITY_ID) is not None
    return ServiceGateway.instances[0]


async def _set_temperature(hass: HomeAssistant, temperature: float) -> None:
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": CLIMATE_ENTITY_ID, "temperature": temperature},
        blocking=True,
    )


async def test_rapid_setpoint_changes_collapse_into_one_write(
    hass: HomeAssistant,
) -> None:
    """Dragging the setpoint slider must reach the gateway once, with the last value.

    PARALLEL_UPDATES = 1 does not serialize this: Home Assistant's single-entity
    service path skips the platform semaphore, so the debounce can coalesce.
    """
    gateway = await _setup(hass)

    await asyncio.gather(*[_set_temperature(hass, 20.0 + step) for step in range(5)])
    await hass.async_block_till_done()

    assert gateway.temperature_writes == [24.0]


async def test_separate_setpoint_changes_each_reach_the_gateway(
    hass: HomeAssistant,
) -> None:
    """Changes further apart than the debounce window are not swallowed."""
    gateway = await _setup(hass)

    await _set_temperature(hass, 21.0)
    await _set_temperature(hass, 23.0)
    await hass.async_block_till_done()

    assert gateway.temperature_writes == [21.0, 23.0]


async def test_setpoint_is_shown_optimistically_before_the_gateway_confirms(
    hass: HomeAssistant,
) -> None:
    """The UI must show the requested setpoint without waiting for a poll."""
    gateway = await _setup(hass)

    await _set_temperature(hass, 24.5)
    await hass.async_block_till_done()

    assert gateway.temperature_writes == [24.5]
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.attributes["temperature"] == 24.5

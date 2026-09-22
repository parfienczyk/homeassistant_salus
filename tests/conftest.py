"""Shared fixtures for Salus integration tests."""

from __future__ import annotations

import asyncio
from dataclasses import is_dataclass, replace
from typing import Any

import pytest
from salus_it600.models import (
    BinarySensorDevice,
    ClimateDevice,
    CoverDevice,
    SensorDevice,
    SwitchDevice,
)

from custom_components.salus.coordinator import SalusData

RAW_PRESET_AWAY = "Away"
RAW_PRESET_ECO = "Eco"
RAW_PRESET_FOLLOW_SCHEDULE = "Follow Schedule"
RAW_PRESET_OFF = "Off"
RAW_PRESET_PERMANENT_HOLD = "Permanent Hold"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


# ---------------------------------------------------------------------------
# Fake gateway and coordinator for entity unit tests
# ---------------------------------------------------------------------------


class FakeGateway:
    """Records gateway method calls for assertion."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.command_error: Exception | None = None

    def _record(self, method: str, *args: Any) -> None:
        if self.command_error is not None:
            raise self.command_error
        self.calls.append((method, *args))

    async def turn_on_switch_device(self, device_id: str) -> None:
        self._record("turn_on_switch", device_id)

    async def turn_off_switch_device(self, device_id: str) -> None:
        self._record("turn_off_switch", device_id)

    async def open_cover(self, device_id: str) -> None:
        self._record("open_cover", device_id)

    async def close_cover(self, device_id: str) -> None:
        self._record("close_cover", device_id)

    async def set_cover_position(self, device_id: str, position: int) -> None:
        self._record("set_cover_position", device_id, position)

    async def set_climate_device_locked(self, device_id: str, locked: bool) -> None:
        self._record("set_climate_locked", device_id, locked)

    async def set_climate_device_temperature(
        self, device_id: str, temperature: float
    ) -> None:
        self._record("set_climate_temperature", device_id, temperature)

    async def set_climate_device_mode(self, device_id: str, mode: str) -> None:
        self._record("set_climate_mode", device_id, mode)

    async def set_climate_device_preset(self, device_id: str, preset: str) -> None:
        self._record("set_climate_preset", device_id, preset)

    async def set_climate_device_fan_mode(self, device_id: str, mode: str) -> None:
        self._record("set_climate_fan_mode", device_id, mode)


class FakeCoordinator:
    """Minimal coordinator fake for entity unit tests.

    Provides the interface that SalusEntity and its subclasses expect:
    - .data (SalusData)
    - .gateway (FakeGateway)
    - .gateway_lock (asyncio.Lock)
    - .gateway_id (str)
    - .async_request_debounced_refresh()
    """

    def __init__(self, data: SalusData | None = None) -> None:
        self.gateway = FakeGateway()
        self.gateway_lock = asyncio.Lock()
        self.gateway_id = "gateway-1"
        self.refresh_requests = 0
        self.last_update_success = True
        self.data = data or SalusData(
            climate_devices={},
            binary_sensor_devices={},
            switch_devices={},
            cover_devices={},
            sensor_devices={},
        )

    async def async_request_debounced_refresh(self) -> None:
        self.refresh_requests += 1


# ---------------------------------------------------------------------------
# Device fixture factories
#
# These build the client's real device models rather than stand-ins, so a
# `salus-it600-client` upgrade that renames or drops a field breaks the suite
# instead of passing against a fake that no longer matches the library.
# ---------------------------------------------------------------------------


def replace_device(device: Any, **changes: Any) -> Any:
    """Return a new snapshot of a device with some fields changed.

    The client rebuilds immutable snapshots on every poll, so this is how a
    device's state changes -- never by mutating a live object.
    """
    if is_dataclass(device):
        return replace(device, **changes)
    return device._replace(**changes)


def deliver_poll(entity: Any, device: Any, **changes: Any) -> Any:
    """Swap a fresh snapshot of one device into the coordinator data.

    Stands in for the coordinator update that carries a new poll's snapshot to
    an entity, which bare unit-test entities never receive.
    """
    updated = replace_device(device, **changes)
    data = entity.coordinator.data
    for collection in (
        data.climate_devices,
        data.binary_sensor_devices,
        data.switch_devices,
        data.cover_devices,
        data.sensor_devices,
    ):
        if device.unique_id in collection:
            collection[device.unique_id] = updated

    # Production does this from `_handle_coordinator_update`, which needs a
    # `hass` these entities do not have.
    invalidate_view_cache = getattr(entity, "_invalidate_view_cache", None)
    if invalidate_view_cache is not None:
        invalidate_view_cache()

    return updated


def make_climate_device(
    unique_id: str = "climate-1",
    name: str = "Living Room",
    *,
    model: str = "SQ610RF",
    available: bool = True,
    temperature_unit: str = "\u00b0C",
    precision: float = 0.1,
    current_temperature: float | None = 21.5,
    current_humidity: float | None = 45.0,
    target_temperature: float = 22.0,
    max_temp: float = 35.0,
    min_temp: float = 5.0,
    hvac_mode: str = "heat",
    hvac_action: str = "heating",
    hvac_modes: list[str] | None = None,
    preset_mode: str = "Permanent Hold",
    preset_modes: list[str] | None = None,
    fan_mode: str | None = None,
    fan_modes: list[str] | None = None,
    locked: bool | None = False,
    supported_features: int = 0,
    device_class: str = "climate",
    data: dict | None = None,
    sw_version: str | None = None,
    extra_state_attributes: dict | None = None,
    hold_type: int | None = 2,
    system_mode: int | None = 4,
    running_state: int | None = 0,
    heating_setpoint: float | None = 22.0,
    cooling_setpoint: float | None = 22.0,
    min_heat_temp: float | None = 5.0,
    max_heat_temp: float | None = 35.0,
    min_cool_temp: float | None = 5.0,
    max_cool_temp: float | None = 35.0,
    heating_control: int | None = 1,
    cooling_control: int | None = 0,
    supports_cooling: bool = True,
    supports_fan: bool = False,
    supports_heat: bool = True,
    online_status: int | None = 1,
    cooling_capability_source: str = "cooling_control",
    diagnostic_fields: dict | None = None,
) -> ClimateDevice:
    """Create a climate device snapshot."""
    if preset_modes is None:
        preset_modes = [
            RAW_PRESET_FOLLOW_SCHEDULE,
            RAW_PRESET_PERMANENT_HOLD,
            RAW_PRESET_OFF,
        ]
        if model in {"SQ610", "SQ610RF"}:
            preset_modes = [
                RAW_PRESET_FOLLOW_SCHEDULE,
                RAW_PRESET_PERMANENT_HOLD,
                RAW_PRESET_AWAY,
                RAW_PRESET_OFF,
            ]
    return ClimateDevice(
        available=available,
        name=name,
        unique_id=unique_id,
        manufacturer="SALUS",
        model=model,
        sw_version=sw_version,
        temperature_unit=temperature_unit,
        precision=precision,
        current_temperature=current_temperature,
        current_humidity=current_humidity,
        target_temperature=target_temperature,
        max_temp=max_temp,
        min_temp=min_temp,
        hvac_mode=hvac_mode,
        hvac_action=hvac_action,
        hvac_modes=tuple(hvac_modes or ["heat", "cool"]),
        preset_mode=preset_mode,
        preset_modes=tuple(preset_modes),
        fan_mode=fan_mode,
        fan_modes=None if fan_modes is None else tuple(fan_modes),
        locked=locked,
        supported_features=supported_features,
        device_class=device_class,
        data=data or {"UniID": unique_id},
        extra_state_attributes=extra_state_attributes,
        hold_type=hold_type,
        system_mode=system_mode,
        running_state=running_state,
        heating_setpoint=heating_setpoint,
        cooling_setpoint=cooling_setpoint,
        min_heat_temp=min_heat_temp,
        max_heat_temp=max_heat_temp,
        min_cool_temp=min_cool_temp,
        max_cool_temp=max_cool_temp,
        heating_control=heating_control,
        cooling_control=cooling_control,
        supports_cooling=supports_cooling,
        supports_fan=supports_fan,
        supports_heat=supports_heat,
        online_status=online_status,
        cooling_capability_source=cooling_capability_source,
        diagnostic_fields=diagnostic_fields or {},
    )


def make_fc600_device(
    unique_id: str = "fc600-1",
    name: str = "Fan Coil",
    **overrides: Any,
) -> ClimateDevice:
    """Create an FC600 fan-coil climate device."""
    defaults: dict[str, Any] = {
        "model": "FC600",
        "hvac_mode": "heat",
        "hvac_modes": ["off", "heat", "cool", "auto"],
        "preset_mode": "Follow Schedule",
        "preset_modes": [
            RAW_PRESET_FOLLOW_SCHEDULE,
            RAW_PRESET_PERMANENT_HOLD,
            RAW_PRESET_ECO,
            RAW_PRESET_OFF,
        ],
        "fan_mode": "Auto",
        "fan_modes": ["Auto", "High", "Medium", "Low", "Off"],
        "locked": None,
        "supports_fan": True,
    }
    defaults.update(overrides)
    return make_climate_device(unique_id=unique_id, name=name, **defaults)


def make_switch_device(
    unique_id: str = "switch-1",
    name: str = "Kitchen Plug",
    *,
    model: str | None = "SPE600",
    is_on: bool = False,
    device_class: str = "outlet",
    available: bool = True,
    data: dict | None = None,
) -> SwitchDevice:
    """Create a switch device snapshot."""
    return SwitchDevice(
        available=available,
        name=name,
        unique_id=unique_id,
        is_on=is_on,
        device_class=device_class,
        data=data or {"UniID": unique_id, "Endpoint": 1},
        manufacturer="SALUS",
        model=model,
        sw_version=None,
    )


def make_cover_device(
    unique_id: str = "cover-1",
    name: str = "Bedroom Blinds",
    *,
    model: str = "RS600",
    current_cover_position: int | None = 75,
    is_opening: bool | None = None,
    is_closing: bool | None = None,
    is_closed: bool = False,
    supported_features: int = 7,  # OPEN | CLOSE | SET_POSITION
    device_class: str | None = None,
    available: bool = True,
    data: dict | None = None,
) -> CoverDevice:
    """Create a cover device snapshot."""
    return CoverDevice(
        available=available,
        name=name,
        unique_id=unique_id,
        current_cover_position=current_cover_position,
        is_opening=is_opening,
        is_closing=is_closing,
        is_closed=is_closed,
        supported_features=supported_features,
        device_class=device_class,
        data=data or {"UniID": unique_id, "Endpoint": 1},
        manufacturer="SALUS",
        model=model,
        sw_version=None,
    )


def make_binary_sensor_device(
    unique_id: str = "binary-1",
    name: str = "Front Door",
    *,
    model: str = "SW600",
    is_on: bool = False,
    device_class: str | None = "window",
    parent_unique_id: str | None = None,
    entity_category: str | None = None,
    extra_state_attributes: dict | None = None,
    available: bool = True,
    data: dict | None = None,
) -> BinarySensorDevice:
    """Create a binary sensor device snapshot."""
    return BinarySensorDevice(
        available=available,
        name=name,
        unique_id=unique_id,
        is_on=is_on,
        device_class=device_class,
        data=data or {"UniID": unique_id},
        manufacturer="SALUS",
        model=model,
        sw_version=None,
        parent_unique_id=parent_unique_id,
        entity_category=entity_category,
        extra_state_attributes=extra_state_attributes,
    )


def make_sensor_device(
    unique_id: str = "sensor-1",
    name: str = "Office Temperature",
    *,
    model: str = "TS600",
    state: Any = 23.4,
    unit_of_measurement: str = "\u00b0C",
    device_class: str = "temperature",
    parent_unique_id: str | None = None,
    entity_category: str | None = None,
    available: bool = True,
    data: dict | None = None,
) -> SensorDevice:
    """Create a sensor device snapshot."""
    return SensorDevice(
        available=available,
        name=name,
        unique_id=unique_id,
        state=state,
        unit_of_measurement=unit_of_measurement,
        device_class=device_class,
        data=data or {"UniID": unique_id, "Endpoint": 1},
        manufacturer="SALUS",
        model=model,
        sw_version=None,
        parent_unique_id=parent_unique_id,
        entity_category=entity_category,
    )

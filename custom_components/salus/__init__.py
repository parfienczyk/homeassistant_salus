"""Support for Salus iT600."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_validation import config_entry_only_config_schema

from salus_it600.exceptions import (
    IT600AuthenticationError,
    IT600ConnectionError,
    IT600UnsupportedFirmwareError,
)
from salus_it600.gateway import IT600Gateway

from .const import (
    CONNECT_RETRIES,
    CONNECT_RETRY_DELAY,
    DOMAIN,
    GATEWAY_CONNECT_TIMEOUT_SECONDS,
    PLATFORMS,
)
from .coordinator import SalusConfigEntry, SalusDataUpdateCoordinator, SalusRuntimeData

CONFIG_SCHEMA = config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: SalusConfigEntry) -> bool:
    """Set up Salus iT600 from a config entry."""
    gateway = IT600Gateway(
        host=entry.data[CONF_HOST],
        euid=entry.data[CONF_TOKEN],
        session=async_get_clientsession(hass),
    )
    runtime_data: SalusRuntimeData | None = None

    try:
        await _async_connect_gateway(gateway)

        coordinator = SalusDataUpdateCoordinator(hass, entry, gateway)
        runtime_data = SalusRuntimeData(gateway=gateway, coordinator=coordinator)
        entry.runtime_data = runtime_data

        await coordinator.async_config_entry_first_refresh()

        gateway_info = gateway.get_gateway_device()
        coordinator.gateway_id = gateway_info.unique_id
        _async_register_gateway_device(hass, entry, gateway_info)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    except Exception:
        with suppress(Exception):
            await gateway.close()
        if (
            runtime_data is not None
            and getattr(entry, "runtime_data", None) is runtime_data
        ):
            del entry.runtime_data
        raise

    return True


async def _async_options_updated(hass: HomeAssistant, entry: SalusConfigEntry) -> None:
    """Reload the config entry when integration options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_connect_gateway(gateway: IT600Gateway) -> None:
    """Connect to the gateway, retrying short-lived connection failures."""
    last_error: Exception | None = None

    for attempt in range(CONNECT_RETRIES):
        try:
            async with asyncio.timeout(GATEWAY_CONNECT_TIMEOUT_SECONDS):
                await gateway.connect()
            return
        except IT600AuthenticationError as ex:
            raise ConfigEntryAuthFailed("Invalid Salus gateway EUID") from ex
        except IT600UnsupportedFirmwareError as ex:
            raise ConfigEntryNotReady(
                "Salus gateway firmware uses an unsupported protocol"
            ) from ex
        except (IT600ConnectionError, TimeoutError) as ex:
            last_error = ex
            if attempt < CONNECT_RETRIES - 1:
                await asyncio.sleep(CONNECT_RETRY_DELAY)

    raise ConfigEntryNotReady("Could not connect to Salus gateway") from last_error


def _async_register_gateway_device(
    hass: HomeAssistant,
    entry: SalusConfigEntry,
    gateway_info: Any,
) -> None:
    """Register the Salus gateway device.

    Creates a Home Assistant device for the gateway itself (parent device for
    all Salus entities). This allows grouping all entities under one device in
    the UI, and provides gateway info (model, firmware version).

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration instance
        gateway_info: Device info from gateway.get_gateway_device()
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_info.unique_id)},
        manufacturer=gateway_info.manufacturer,
        name=gateway_info.name,
        model=gateway_info.model,
        sw_version=gateway_info.sw_version,
    )
    _async_remove_stale_mac_connection(
        device_registry,
        device,
        gateway_info.unique_id,
    )


def _async_remove_stale_mac_connection(
    device_registry: dr.DeviceRegistry,
    device: dr.DeviceEntry,
    gateway_unique_id: str,
) -> None:
    """Drop the MAC connection earlier versions stored for the gateway.

    The gateway EUID is a ZigBee EUI-64, not a MAC address, so registering it
    under CONNECTION_NETWORK_MAC described the device incorrectly. Identifiers
    still match the existing device, so removing the connection keeps it and
    its entities intact.
    """
    stale_connections = {(dr.CONNECTION_NETWORK_MAC, gateway_unique_id)}
    if not stale_connections & device.connections:
        return

    device_registry.async_update_device(
        device.id,
        new_connections=device.connections - stale_connections,
    )


async def async_unload_entry(hass: HomeAssistant, entry: SalusConfigEntry) -> bool:
    """Unload a config entry."""
    runtime_data = entry.runtime_data
    runtime_data.coordinator.async_cancel_debounced_refresh()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await runtime_data.gateway.close()

    return unload_ok

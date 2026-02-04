"""The vizio component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyvizio import VizioAsync

from homeassistant.components.media_player import MediaPlayerDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_CLASS,
    CONF_HOST,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import CONF_APPS, DEFAULT_TIMEOUT, DEVICE_ID, DOMAIN, VIZIO_DEVICE_CLASSES
from .coordinator import VizioAppsDataUpdateCoordinator, VizioDeviceCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.MEDIA_PLAYER]


@dataclass
class VizioRuntimeData:
    """Runtime data for Vizio integration."""

    device: VizioAsync
    device_coordinator: VizioDeviceCoordinator
    apps_coordinator: VizioAppsDataUpdateCoordinator | None  # None for speakers


type VizioConfigEntry = ConfigEntry[VizioRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the component."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: VizioConfigEntry) -> bool:
    """Load the saved entities."""
    host = entry.data[CONF_HOST]
    token = entry.data.get(CONF_ACCESS_TOKEN)
    device_class = entry.data[CONF_DEVICE_CLASS]

    hass.data.setdefault(DOMAIN, {})

    # Create device
    device = VizioAsync(
        DEVICE_ID,
        host,
        "",
        auth_token=token,
        device_type=VIZIO_DEVICE_CLASSES[device_class],
        session=async_get_clientsession(hass, False),
        timeout=DEFAULT_TIMEOUT,
    )

    # Create device coordinator
    device_coordinator = VizioDeviceCoordinator(hass, entry, device)
    await device_coordinator.async_config_entry_first_refresh()

    # Create apps coordinator for TVs (shared across entries)
    apps_coordinator: VizioAppsDataUpdateCoordinator | None = None
    if device_class == MediaPlayerDeviceClass.TV:
        if CONF_APPS not in hass.data[DOMAIN]:
            store: Store[list[dict[str, Any]]] = Store(hass, 1, DOMAIN)
            apps_coordinator = VizioAppsDataUpdateCoordinator(hass, entry, store)
            await apps_coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][CONF_APPS] = apps_coordinator
        else:
            apps_coordinator = hass.data[DOMAIN][CONF_APPS]

    # Store runtime data
    entry.runtime_data = VizioRuntimeData(
        device=device,
        device_coordinator=device_coordinator,
        apps_coordinator=apps_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: VizioConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up apps coordinator if no TV entries remain
    if unload_ok and not any(
        e.data[CONF_DEVICE_CLASS] == MediaPlayerDeviceClass.TV
        for e in hass.config_entries.async_loaded_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ):
        hass.data[DOMAIN].pop(CONF_APPS, None)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok

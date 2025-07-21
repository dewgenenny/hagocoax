"""Initialize the GoCoax integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

PLATFORMS: list[str] = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """
    Set up the GoCoax integration from YAML (if any).
    Usually, if you're only using config flow, this can be almost empty.
    """
    # We are using config_flow-based setup only, so just return True.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Set up a GoCoax device from a config entry.
    This is called after the user completes the config flow.
    """
    # Forward the entry setup to the sensor platform so that
    # sensor.py's async_setup_entry is called. Home Assistant 2025.6
    # replaced ``async_forward_entry_setup`` with ``async_forward_entry_setups``.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Unload a GoCoax config entry.
    Called when a user removes the integration or disables it.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

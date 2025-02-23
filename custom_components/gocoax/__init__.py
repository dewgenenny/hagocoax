"""Initialize the GoCoax integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .sensor import async_setup_entry as async_setup_sensors

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the GoCoax integration (YAML not used with config flow)."""
    # If your integration does not support YAML-based config, just return True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a GoCoax device from a config entry."""
    # Forward the entry setup to the sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a GoCoax config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return unload_ok

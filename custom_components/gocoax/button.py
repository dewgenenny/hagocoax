"""GoCoax button platform."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_HOST
from .sensor import GoCoaxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GoCoaxRebootButton(coordinator),
        GoCoaxRestoreButton(coordinator),
    ])


class GoCoaxRebootButton(CoordinatorEntity, ButtonEntity):
    """Button that reboots the GoCoax adapter."""

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_reboot"
        self._attr_name = "GoCoax Reboot"
        self._attr_icon = "mdi:restart"

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(self.coordinator.api.reboot)

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )


class GoCoaxRestoreButton(CoordinatorEntity, ButtonEntity):
    """Button that restores factory defaults and reboots."""

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_restore"
        self._attr_name = "GoCoax Restore Defaults"
        self._attr_icon = "mdi:restore"

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(self.coordinator.api.restore)

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )

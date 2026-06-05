"""GoCoax switch platform - boolean MoCA settings."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .sensor import GoCoaxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GoCoaxPreferredNcSwitch(coordinator),
        GoCoaxNetworkSearchSwitch(coordinator),
    ])


class _GoCoaxBoolSwitch(CoordinatorEntity, SwitchEntity):

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._do_write, True)
        _LOGGER.info("GoCoax setting changed; reboot required for it to take effect")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._do_write, False)
        _LOGGER.info("GoCoax setting changed; reboot required for it to take effect")
        await self.coordinator.async_request_refresh()

    def _do_write(self, enabled: bool) -> None:
        raise NotImplementedError

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )


class GoCoaxPreferredNcSwitch(_GoCoaxBoolSwitch):
    _attr_icon = "mdi:crown"

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_preferred_nc"
        self._attr_name = "GoCoax Preferred NC"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.get("preferred_nc") if data else None

    def _do_write(self, enabled: bool) -> None:
        self.coordinator.api.set_preferred_nc(enabled)


class GoCoaxNetworkSearchSwitch(_GoCoaxBoolSwitch):
    _attr_icon = "mdi:magnify"

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_network_search"
        self._attr_name = "GoCoax Network Search"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.get("network_search") if data else None

    def _do_write(self, enabled: bool) -> None:
        self.coordinator.api.set_network_search(enabled)

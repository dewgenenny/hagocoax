"""GoCoax number platform - writable RF power settings."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
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
        GoCoaxTxPowerNumber(coordinator),
        GoCoaxBeaconPowerNumber(coordinator),
    ])


class _GoCoaxPowerNumber(CoordinatorEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(self._do_write, int(value))
        _LOGGER.info("GoCoax setting changed; reboot required for it to take effect")
        await self.coordinator.async_request_refresh()

    def _do_write(self, value: int) -> None:
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


class GoCoaxTxPowerNumber(_GoCoaxPowerNumber):
    _attr_icon = "mdi:signal"

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_tx_power"
        self._attr_name = "GoCoax TX Power"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.get("tx_power") if data else None

    def _do_write(self, value: int) -> None:
        self.coordinator.api.set_tx_power(value)


class GoCoaxBeaconPowerNumber(_GoCoaxPowerNumber):
    _attr_icon = "mdi:signal-variant"

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_beacon_power_level"
        self._attr_name = "GoCoax Beacon Power Level"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.get("beacon_power_level") if data else None

    def _do_write(self, value: int) -> None:
        self.coordinator.api.set_beacon_power_level(value)

"""GoCoax binary sensor platform."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .sensor import GoCoaxCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GoCoaxLinkBinarySensor(coordinator)])


class GoCoaxLinkBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """True when the MoCA link is up."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: GoCoaxCoordinator):
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_link_binary"
        self._attr_name = "GoCoax Link"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("link_status") == "Up"

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )

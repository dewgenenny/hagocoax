"""GoCoax sensor platform."""

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,  # e.g. 60
)
from .gocoax_api import GoCoaxAPI  # Where your real MoCA logic & requests live

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Set up GoCoax sensors from a config entry.
    Called by HA when the user completes config flow or on startup.
    """
    coordinator = GoCoaxCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        _LOGGER.warning("Initial connection to GoCoax failed; check credentials/logs")

    # Create one Sensor entity per item in SENSORS
    sensors = []
    for sensor_key, sensor_name in SENSORS.items():
        sensors.append(GoCoaxSensor(coordinator, sensor_key, sensor_name))

    async_add_entities(sensors)


class GoCoaxCoordinator(DataUpdateCoordinator):
    """
    Coordinator to fetch data from GoCoax on a schedule.
    This is how we keep sensor values fresh.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator with a reference to HA, the config entry, etc."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"GoCoax({entry.data[CONF_HOST]})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry

        # Build the API client using credentials from the config entry
        host = entry.data[CONF_HOST]
        username = entry.data[CONF_USERNAME]
        password = entry.data[CONF_PASSWORD]
        self.api = GoCoaxAPI(host, username, password)

    async def _async_update_data(self):
        """
        Get updated data from the device asynchronously.
        Run the real logic in an executor thread to avoid blocking the event loop.
        """
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self):
        """
        Synchronous function to do the actual I/O with requests.
        Calls into GoCoaxAPI to gather all data and parse it.
        """
        try:
            raw_info = self.api.retrieve_device_info()
            processed = self.api.display_device_info(raw_info)
            return processed
        except Exception as err:
            raise UpdateFailed(f"Error updating GoCoax data: {err}") from err


# Dict that maps data keys to a friendly name for the sensor
SENSORS = {
    "soc_version": "SoC Version",
    "my_moca_version": "My MoCA Version",
    "network_moca_version": "Network MoCA Version",
    "ip_address": "IP Address",
    "mac_address": "MAC Address",
    "link_status": "Link Status",
    "lof": "LOF",
    "eth_tx_good": "Ethernet TX Good",
    "eth_tx_bad": "Ethernet TX Bad",
    "eth_tx_dropped": "Ethernet TX Dropped",
    "eth_rx_good": "Ethernet RX Good",
    "eth_rx_bad": "Ethernet RX Bad",
    "eth_rx_dropped": "Ethernet RX Dropped",
}


class GoCoaxSensor(CoordinatorEntity, SensorEntity):
    """
    A single sensor entity for one key in the GoCoax data dictionary.
    """

    def __init__(self, coordinator: GoCoaxCoordinator, sensor_key: str, sensor_name: str):
        """Initialize the sensor with a key that references the coordinator data."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_name = f"GoCoax {sensor_name}"

        # Build a unique ID based on the device's host + sensor key
        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_{sensor_key}"

    @property
    def native_value(self):
        """Return the sensor's current value, pulled from coordinator.data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._sensor_key)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """
        Group all sensors for this host into one 'device' in the HA UI.
        """
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )

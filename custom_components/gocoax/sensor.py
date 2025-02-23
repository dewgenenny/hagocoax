"""GoCoax sensor platform (with PHY rates included)."""

import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
)
from .gocoax_api import GoCoaxAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Set up GoCoax sensors from a config entry.
    This includes both standard sensors (SoC version, link, etc.)
    and dynamic sensors for PHY rates among discovered MoCA nodes.
    """
    coordinator = GoCoaxCoordinator(hass, entry)
    # Do the first refresh so we have data to discover node IDs
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Initial connection to GoCoax failed; check credentials/logs"
        )

    # 1) Create standard "main" sensors (device info, link status, etc.)
    main_sensors = []
    for definition in MAIN_SENSORS:
        main_sensors.append(GoCoaxSensor(coordinator, definition))

    # 2) Create dynamic sensors for PHY Rates, based on discovered nodes
    phy_rate_sensors = []
    data = coordinator.data or {}
    phy_data = data.get("phy_rates_data")  # dict with "nodes", "rates", "gcd_rates"
    if phy_data:
        node_list = phy_data.get("nodes", [])
        gcd_rates = phy_data.get("gcd_rates", [])
        rate_matrix = phy_data.get("rates", [])

        # a) GCD sensors: one per node
        for idx, node_id in enumerate(node_list):
            phy_rate_sensors.append(
                GoCoaxPhyGcdRateSensor(
                    coordinator,
                    node_id=node_id,
                    gcd_rate_index=idx
                )
            )

        # b) Node-to-Node rates: one sensor per pair
        for i, node_from in enumerate(node_list):
            for j, node_to in enumerate(node_list):
                # A sensor for "PHY Rate from node_from to node_to"
                phy_rate_sensors.append(
                    GoCoaxPhyRateSensor(
                        coordinator,
                        node_from=node_from,
                        node_to=node_to,
                        from_index=i,
                        to_index=j
                    )
                )

    all_sensors = main_sensors + phy_rate_sensors
    async_add_entities(all_sensors)


class GoCoaxCoordinator(DataUpdateCoordinator):
    """
    Coordinator that fetches device info plus PHY rates.
    Stores them in self.data for consumption by sensors.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=f"GoCoax({entry.data[CONF_HOST]})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry

        host = entry.data[CONF_HOST]
        username = entry.data[CONF_USERNAME]
        password = entry.data[CONF_PASSWORD]
        self.api = GoCoaxAPI(host, username, password)

    async def _async_update_data(self):
        """Fetch data from the device in a background thread."""
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self):
        """
        Synchronous I/O:
        1) Retrieve main device info
        2) Parse it
        3) Also get PHY rates
        4) Merge everything into a single dictionary
        """
        try:
            # Main device info
            raw_info = self.api.retrieve_device_info()
            processed_info = self.api.display_device_info(raw_info)

            # Also fetch PHY rates
            phy_data = self.api.get_phy_rates(debug=False)  # returns {nodes, rates, gcd_rates}
            if phy_data:
                processed_info["phy_rates_data"] = phy_data

            return processed_info
        except Exception as err:
            raise UpdateFailed(f"Error updating GoCoax data: {err}") from err


# ------------------------------------------------------------------------------
# MAIN_SENSORS: define "regular" sensor fields from display_device_info
# ------------------------------------------------------------------------------
MAIN_SENSORS = [
    {
        "key": "soc_version",
        "name": "SoC Version",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:chip",
    },
    {
        "key": "my_moca_version",
        "name": "My MoCA Version",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:chip",
    },
    {
        "key": "network_moca_version",
        "name": "Network MoCA Version",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:chip",
    },
    {
        "key": "ip_address",
        "name": "IP Address",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:lan",
    },
    {
        "key": "mac_address",
        "name": "MAC Address",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:lan",
    },
    {
        "key": "link_status",
        "name": "Link Status",
        "device_class": None,
        "state_class": None,
        "unit_of_measurement": None,
        "icon": "mdi:lan-connect",
    },
    {
        "key": "lof",
        "name": "LOF",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit_of_measurement": None,
        "icon": "mdi:access-point-network",
    },
    # Ethernet counters
    {
        "key": "eth_tx_good",
        "name": "Ethernet TX Good",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:upload-network",
    },
    {
        "key": "eth_tx_bad",
        "name": "Ethernet TX Bad",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:close-network",
    },
    {
        "key": "eth_tx_dropped",
        "name": "Ethernet TX Dropped",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:close-network",
    },
    {
        "key": "eth_rx_good",
        "name": "Ethernet RX Good",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:download-network",
    },
    {
        "key": "eth_rx_bad",
        "name": "Ethernet RX Bad",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:close-network",
    },
    {
        "key": "eth_rx_dropped",
        "name": "Ethernet RX Dropped",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": "packets",
        "icon": "mdi:close-network",
    },
]


class GoCoaxSensor(CoordinatorEntity, SensorEntity):
    """
    A single "main" sensor for a known key in the processed_info dictionary.
    """

    def __init__(self, coordinator: GoCoaxCoordinator, definition: dict):
        super().__init__(coordinator)
        self._definition = definition
        self._attr_name = f"GoCoax {definition['name']}"

        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_{definition['key']}"
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self._attr_native_unit_of_measurement = definition.get("unit_of_measurement")
        self._attr_icon = definition.get("icon")

    @property
    def native_value(self):
        """Return the sensor value from coordinator.data."""
        data = self.coordinator.data
        if not data:
            return None

        key = self._definition["key"]
        value = data.get(key)

        # Convert to integer if state_class indicates it's numeric
        if self._attr_state_class in (SensorStateClass.TOTAL_INCREASING, SensorStateClass.MEASUREMENT):
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    value = None
        return value

    @property
    def device_info(self) -> DeviceInfo:
        """Group all sensors under one device using the host as identifier."""
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )


# ------------------------------------------------------------------------------
# Dynamic sensors for PHY rates: GCD per node, and node->node rates in Mbps
# ------------------------------------------------------------------------------
class GoCoaxPhyGcdRateSensor(CoordinatorEntity, SensorEntity):
    """
    One sensor for each node's GCD (general cable diagnostics) in the PHY rates.
    """

    def __init__(self, coordinator: GoCoaxCoordinator, node_id: int, gcd_rate_index: int):
        super().__init__(coordinator)
        self._node_id = node_id
        self._gcd_rate_index = gcd_rate_index

        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_gcd_rate_node_{node_id}"
        self._attr_name = f"GoCoax GCD Rate (Node {node_id})"
        self._attr_native_unit_of_measurement = "Mbps"
        self._attr_state_class = SensorStateClass.MEASUREMENT  # treat it as a measurement
        self._attr_icon = "mdi:swap-horizontal"

    @property
    def native_value(self):
        """Return the GCD rate for this node from coordinator.data."""
        data = self.coordinator.data
        if not data:
            return None

        phy_data = data.get("phy_rates_data", {})
        gcd = phy_data.get("gcd_rates", [])
        if self._gcd_rate_index < len(gcd):
            return gcd[self._gcd_rate_index]
        return None

    @property
    def device_info(self):
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )


class GoCoaxPhyRateSensor(CoordinatorEntity, SensorEntity):
    """
    One sensor for each pair of nodes in the "rates" 2D matrix.
    It shows the PHY rate from node_from to node_to in Mbps.
    """

    def __init__(self, coordinator: GoCoaxCoordinator, node_from: int, node_to: int, from_index: int, to_index: int):
        super().__init__(coordinator)
        self._node_from = node_from
        self._node_to = node_to
        self._from_index = from_index
        self._to_index = to_index

        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_phy_rate_from_{node_from}_to_{node_to}"
        self._attr_name = f"PHY Rate from {node_from} to {node_to}"
        self._attr_native_unit_of_measurement = "Mbps"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:swap-horizontal"

    @property
    def native_value(self):
        """Return the from->to rate from coordinator.data's 2D matrix."""
        data = self.coordinator.data
        if not data:
            return None

        phy_data = data.get("phy_rates_data", {})
        rate_matrix = phy_data.get("rates", [])

        # Make sure indexes exist
        if self._from_index < len(rate_matrix):
            row = rate_matrix[self._from_index]
            if self._to_index < len(row):
                return row[self._to_index]

        return None

    @property
    def device_info(self):
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )

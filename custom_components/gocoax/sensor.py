"""GoCoax sensor platform."""
import logging
from datetime import timedelta
import requests
from requests.auth import HTTPDigestAuth  # If needed for digest
import urllib3

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.helpers.entity import DeviceInfo

# Import constants from our const.py
# Adjust the imports if your const.py uses different names
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# The main entry point for the sensor platform. Home Assistant calls this
# when setting up the "sensor" domain for our integration. We:
# 1) Create the DataUpdateCoordinator
# 2) Do an immediate refresh
# 3) Create sensor entities for each metric we want to expose
# ---------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up GoCoax sensors from a config entry."""
    coordinator = GoCoaxCoordinator(hass, entry)
    # Perform the first refresh to get initial data before creating the entities
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Initial connection to GoCoax failed; please check logs or credentials."
        )

    # Create a sensor for each metric (dictionary key) we want to track
    sensors = []
    for sensor_key, sensor_name in SENSORS.items():
        sensors.append(GoCoaxSensor(coordinator, sensor_key, sensor_name))

    async_add_entities(sensors)


# ---------------------------------------------------------------------------
# SENSORS dict: map keys in the data dictionary to a friendly sensor name
# ---------------------------------------------------------------------------
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
    # You could also add any additional fields if you incorporate PHY rates, etc.
}


# ---------------------------------------------------------------------------
# DataUpdateCoordinator: manages scheduling and fetching updated data
# ---------------------------------------------------------------------------
class GoCoaxCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from GoCoax adapter on a regular interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry

        super().__init__(
            hass,
            _LOGGER,
            name=f"GoCoax({entry.data[CONF_HOST]})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        # Prepare an instance of our GoCoaxAPI class with the user's config
        host = entry.data[CONF_HOST]
        username = entry.data[CONF_USERNAME]
        password = entry.data[CONF_PASSWORD]

        self.api = GoCoaxAPI(host, username, password)

    async def _async_update_data(self):
        """Fetch data from the device. Runs in the event loop (async)."""
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self):
        """Perform the actual requests synchronously in a thread executor."""
        try:
            # 1) Retrieve raw data from the device
            device_info = self.api.retrieve_device_info()

            # 2) Process/parse it into a dictionary of sensor-friendly metrics
            processed = self.api.display_device_info(device_info)  # returns a dict

            # 3) (Optional) retrieve PHY rates if you want more sensors
            # phy_rates_data = self.api.get_phy_rates()  # Also returns some data
            # Merge into final dictionary if you want:
            # processed["phy_rates"] = phy_rates_data

            return processed
        except Exception as err:
            raise UpdateFailed(f"Error updating GoCoax data: {err}") from err


# ---------------------------------------------------------------------------
# The main sensor entity class that reads data from the coordinator
# ---------------------------------------------------------------------------
class GoCoaxSensor(CoordinatorEntity, SensorEntity):
    """A sensor for a single GoCoax metric."""

    def __init__(self, coordinator: GoCoaxCoordinator, sensor_key: str, sensor_name: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_name = f"GoCoax {sensor_name}"

        host = coordinator.entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_{sensor_key}"

    @property
    def native_value(self):
        """Return the sensor value from the coordinator data."""
        data = self.coordinator.data
        if not data:
            return None
        return data.get(self._sensor_key)

    @property
    def device_info(self) -> DeviceInfo:
        """Group all sensors for this host as one device in HA."""
        host = self.coordinator.entry.data[CONF_HOST]
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"GoCoax ({host})",
            manufacturer="GoCoax / MaxLinear",
            model="MoCA Adapter",
        )


# ---------------------------------------------------------------------------
# The API code: adapted from your original script. Some code is shortened
# or reorganized, but the logic is the same.
# ---------------------------------------------------------------------------
class GoCoaxAPI:
    """Python API for GoCoax MoCA Adapters, using requests and your original parsing logic."""

    def __init__(self, host, username, password):
        """Initialize with credentials."""
        self._base_url = f"http://{host}"
        self._session = requests.Session()

        # If your device only needs basic auth:
        self._session.auth = (username, password)

        # If your device uses Digest Authentication, do:
        # self._session.auth = HTTPDigestAuth(username, password)

        # Turn off warnings for self-signed certificates, if needed
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Define endpoints (same as your original script)
        self.endpoints = {
            'devStatus': '/devStatus.html',   # to retrieve the CSRF token
            'phyRates': '/phyRates.html',
            'localInfo': '/ms/0/0x15',
            'netInfo': '/ms/0/0x16',
            'fmrInfo': '/ms/0/0x1D',
            'miscphyinfo': '/ms/0/0x24',
            'macInfo': '/ms/1/0x103/GET',
            'frameInfo': '/ms/0/0x14',
            'lof': '/ms/0/0x1003/GET',
            'ipAddr': '/ms/1/0x20b/GET',
            'ChipID': '/ms/1/0x303/GET',
            'gpio': '/ms/1/0xb17',
            'miscm25phyinfo': '/ms/0/0x7f',
        }

    # ---------------------------
    # Core request helpers
    # ---------------------------
    def get_csrf_token(self):
        """Extract the CSRF token from the session cookies, if available."""
        return self._session.cookies.get('csrf_token')

    def post_data(self, action_url, payload_dict=None, referer=None, payload_format='json'):
        """Perform a POST request with optional JSON payload, returning the parsed JSON."""
        url = self._base_url + action_url
        csrf_token = self.get_csrf_token()

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Connection': 'keep-alive',
            'Origin': self._base_url,
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        # Use devStatus.html as default referer if none provided
        headers['Referer'] = self._base_url + (referer if referer else self.endpoints['devStatus'])

        if payload_format == 'json':
            headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
            headers['Content-Type'] = 'application/json'
            if payload_dict is None:
                payload_dict = {"data": []}
            data_to_send = payload_dict
        else:
            headers['Accept'] = 'text/html, */*'
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            if payload_dict is None:
                payload_dict = {}
            data_to_send = payload_dict

        if csrf_token:
            headers['X-CSRF-TOKEN'] = csrf_token
            headers['Cookie'] = f'csrf_token={csrf_token}'

        resp = self._session.post(url, json=data_to_send, headers=headers, verify=False)
        resp.raise_for_status()
        return resp.json()

    def get_data(self, action_url, referer=None):
        """Perform a GET request, returning the raw requests.Response."""
        url = self._base_url + action_url
        csrf_token = self.get_csrf_token()

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html, */*',
            'Connection': 'keep-alive',
        }
        if referer:
            headers['Referer'] = self._base_url + referer
        if csrf_token:
            headers['X-CSRF-TOKEN'] = csrf_token
            headers['Cookie'] = f'csrf_token={csrf_token}'

        resp = self._session.get(url, headers=headers, verify=False)
        resp.raise_for_status()
        return resp

    # ---------------------------
    # Retrieve raw device info
    # (From your original script)
    # ---------------------------
    def retrieve_device_info(self):
        """Collect many device info fields and return them as a dict of raw data."""
        # Step 1: get devStatus.html to initialize CSRF
        dev_status_url = self._base_url + self.endpoints['devStatus']
        resp = self._session.get(dev_status_url, verify=False)
        resp.raise_for_status()

        csrf_token = self.get_csrf_token()
        if not csrf_token:
            raise ValueError("Failed to retrieve CSRF token from GoCoax device.")

        device_info = {}

        # localInfo
        local_info = self.post_data(self.endpoints['localInfo'])
        device_info['localInfo'] = local_info['data']
        myNodeId = int(device_info['localInfo'][0], 16)

        # miscphyinfo
        miscphyinfo = self.post_data(self.endpoints['miscphyinfo'])
        device_info['miscphyinfo'] = miscphyinfo['data']

        # netInfo
        payload_dict = {"data": [myNodeId]}
        net_info = self.post_data(self.endpoints['netInfo'], payload_dict=payload_dict)
        device_info['netInfo'] = net_info['data']

        # macInfo
        mac_info = self.post_data(self.endpoints['macInfo'], payload_dict={"data": [myNodeId]})
        device_info['macInfo'] = mac_info['data']

        # frameInfo
        frame_info = self.post_data(self.endpoints['frameInfo'], payload_dict={"data": [0]})
        device_info['frameInfo'] = frame_info['data']

        # lof
        lof = self.post_data(self.endpoints['lof'])
        device_info['lof'] = lof['data']

        # ipAddr
        ip_addr = self.post_data(self.endpoints['ipAddr'])
        device_info['ipAddr'] = ip_addr['data']

        # chipId
        chip_id = self.post_data(self.endpoints['ChipID'])
        device_info['chipId'] = chip_id['data']

        # gpio
        gpio = self.post_data(self.endpoints['gpio'], payload_dict={"data": [0]})
        device_info['gpio'] = gpio['data']

        # miscm25phyinfo
        miscm25phyinfo = self.post_data(self.endpoints['miscm25phyinfo'])
        device_info['miscm25phyinfo'] = miscm25phyinfo['data']

        return device_info

    # ---------------------------
    # Helper conversions
    # (Same as your script)
    # ---------------------------
    def byte2ascii(self, hex_str):
        try:
            bytes_obj = bytes.fromhex(hex_str)
            ascii_str = ''
            for b in bytes_obj:
                if 0 < b < 0x80:
                    ascii_str += chr(b)
                else:
                    return ''
            return ascii_str
        except ValueError:
            return ''

    def hex2mac(self, hi, lo):
        mac_parts = [
            f"{(hi >> 24) & 0xFF:02x}",
            f"{(hi >> 16) & 0xFF:02x}",
            f"{(hi >> 8) & 0xFF:02x}",
            f"{hi & 0xFF:02x}",
            f"{(lo >> 24) & 0xFF:02x}",
            f"{(lo >> 16) & 0xFF:02x}",
        ]
        return ':'.join(mac_parts)

    # ---------------------------
    # Processes the raw info into
    # a dictionary of sensor values
    # (Derived from display_device_info)
    # ---------------------------
    def display_device_info(self, device_info):
        """Parse all raw data and return key metrics as a dict to feed sensors."""
        local_info = device_info['localInfo']
        miscphyinfo = device_info['miscphyinfo']
        net_info = device_info['netInfo']
        mac_info = device_info['macInfo']
        frame_info = device_info['frameInfo']
        lof = device_info['lof']
        ip_addr = device_info['ipAddr']
        chip_id = device_info['chipId']
        gpio = device_info['gpio']
        miscm25phyinfo = device_info['miscm25phyinfo']

        # Network MoCA Version
        nwMocaVer = int(local_info[11], 16)
        nwMocaVerVal = f"{(nwMocaVer >> 4) & 0xF}.{nwMocaVer & 0xF}"

        # Link Status
        linkStatus = int(local_info[5], 16)
        linkStatusVal = "Up" if linkStatus else "Down"

        # SoC version
        socVersion = ''
        i = 0
        while True:
            idx = 21 + i
            if idx >= len(local_info):
                break
            val = local_info[idx][2:10]
            retVal = self.byte2ascii(val)
            if not retVal:
                break
            socVersion += retVal
            i += 1

        # Determine chip name
        chipArray = ["MXL370x", "MXL371x", "UNKNOWN"]
        chipIdInt = int(chip_id[0], 16)
        chipIdIndex = chipIdInt - 0x15
        if chipIdIndex >= len(chipArray):
            chipIdIndex = len(chipArray) - 1
        chipName = chipArray[chipIdIndex]
        socVersionVal = f"{chipName}.{socVersion}"

        # MAC Address
        hi = int(mac_info[0], 16)
        lo = int(mac_info[1], 16)
        macAddressVal = self.hex2mac(hi, lo)

        # My MoCA Version
        myMocaVer = int(net_info[4], 16)
        myMocaVerVal = f"{(myMocaVer >> 4) & 0xF}.{myMocaVer & 0xF}"

        # Ethernet TX stats
        txgood = ((int(frame_info[12], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[13], 16)
        txbad = ((int(frame_info[30], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[31], 16)
        txdropped = ((int(frame_info[48], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[49], 16)

        # Ethernet RX stats
        rxgood = ((int(frame_info[66], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[67], 16)
        rxbad = ((int(frame_info[84], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[85], 16)
        rxdropped = ((int(frame_info[102], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[103], 16)

        # IP Address
        ipAddrInt = int(ip_addr[0], 16)
        ipAddrVal = f"{(ipAddrInt >> 24) & 0xFF}.{(ipAddrInt >> 16) & 0xFF}.{(ipAddrInt >> 8) & 0xFF}.{ipAddrInt & 0xFF}"

        # LOF
        lofVal = int(lof[0], 16)

        # Return as a dictionary that matches our SENSORS keys
        return {
            "soc_version": socVersionVal,
            "my_moca_version": myMocaVerVal,
            "network_moca_version": nwMocaVerVal,
            "ip_address": ipAddrVal,
            "mac_address": macAddressVal,
            "link_status": linkStatusVal,
            "lof": lofVal,
            "eth_tx_good": txgood,
            "eth_tx_bad": txbad,
            "eth_tx_dropped": txdropped,
            "eth_rx_good": rxgood,
            "eth_rx_bad": rxbad,
            "eth_rx_dropped": rxdropped,
        }

    # -----------------------------------------------------------------------
    # Optional: If you also want to gather PHY rates as part of your data,
    # you can add your original get_phy_rates function here as well,
    # returning a dictionary. Then in _fetch_data() you'd call it & merge
    # the results in your final dictionary. For brevity, it's omitted here.
    # -----------------------------------------------------------------------

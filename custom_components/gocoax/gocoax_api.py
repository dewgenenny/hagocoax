"""Helper API calls for GoCoax integration."""

import requests
from requests.auth import HTTPDigestAuth  # Uncomment if the device uses digest
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def validate_connection(host: str, username: str, password: str) -> bool:
    """
    Attempt to retrieve the devStatus page to confirm credentials are valid.
    Used by config_flow to test connection before creating a config entry.
    """
    base_url = f"http://{host}"
    session = requests.Session()

    # If the device only needs Basic Auth:
    session.auth = (username, password)

    # If the device needs Digest Auth, then use:
    # session.auth = HTTPDigestAuth(username, password)

    dev_status_url = base_url + "/devStatus.html"
    response = session.get(dev_status_url, verify=False, timeout=5)
    response.raise_for_status()

    # If we got here with no exception, we assume credentials/connection are valid
    return True


class GoCoaxAPI:
    """
    A Python API for GoCoax MoCA Adapters, adapted from your original script.
    Provides methods to:
      - retrieve_device_info()   -> returns raw device data
      - display_device_info()    -> parse the raw data into sensor-friendly fields
      - (Optionally) get_phy_rates() for advanced MoCA rates, if desired.
    """

    def __init__(self, host: str, username: str, password: str):
        """
        Initialize the GoCoaxAPI with credentials and set up the session.
        """
        self._base_url = f"http://{host}"
        self._session = requests.Session()

        # Basic Auth by default:
        self._session.auth = (username, password)

        # For Digest Auth (uncomment if needed):
        # self._session.auth = HTTPDigestAuth(username, password)

        # Endpoints from your original code
        self.endpoints = {
            'devStatus': '/devStatus.html',   # to retrieve the CSRF token
            'phyRates': '/phyRates.html',     # for referer in the headers
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

    # --------------------------------------------------------------------------------
    # Simple request helpers
    # --------------------------------------------------------------------------------
    def get_csrf_token(self):
        """Return the current CSRF token from session cookies, if any."""
        return self._session.cookies.get('csrf_token')

    def post_data(self, action_url, payload_dict=None, referer=None, payload_format='json'):
        """
        Perform a POST request with optional JSON or form payload, returning the parsed JSON.
        Adjusted from your original code.
        """
        url = self._base_url + action_url
        csrf_token = self.get_csrf_token()

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Connection': 'keep-alive',
            'Origin': self._base_url,
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        # Default referer if none provided
        headers['Referer'] = self._base_url + (referer if referer else self.endpoints['devStatus'])

        # If JSON payload
        if payload_format == 'json':
            headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
            headers['Content-Type'] = 'application/json'
            if payload_dict is None:
                payload_dict = {"data": []}
            data_to_send = payload_dict

        # If form data
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
        """
        Perform a GET request, returning a requests.Response (not JSON-decoded).
        """
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

    # --------------------------------------------------------------------------------
    # Retrieve device info (raw data) - from your original code
    # --------------------------------------------------------------------------------
    def retrieve_device_info(self):
        """
        Hit devStatus.html to get CSRF token, then gather multiple MoCA data points
        (localInfo, netInfo, macInfo, frameInfo, etc.). Return them in a dictionary.
        """
        # 1) Access devStatus to get CSRF
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

    # --------------------------------------------------------------------------------
    # Helpers for display_device_info
    # --------------------------------------------------------------------------------
    def byte2ascii(self, hex_str):
        """Convert a hex string to ASCII, ignoring out-of-range bytes."""
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
        """Convert two integers hi & lo into a MAC address string."""
        mac_parts = [
            f"{(hi >> 24) & 0xFF:02x}",
            f"{(hi >> 16) & 0xFF:02x}",
            f"{(hi >> 8) & 0xFF:02x}",
            f"{hi & 0xFF:02x}",
            f"{(lo >> 24) & 0xFF:02x}",
            f"{(lo >> 16) & 0xFF:02x}",
        ]
        return ':'.join(mac_parts)

    # --------------------------------------------------------------------------------
    # Processes the raw device_info into a dictionary of sensor-friendly values
    # (Essentially your display_device_info logic, but returning data instead of printing)
    # --------------------------------------------------------------------------------
    def display_device_info(self, device_info):
        """
        Convert the raw data from retrieve_device_info() into a dictionary
        suitable for sensor values: SoC version, IP, link status, etc.
        """
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

        # MoCA versions
        nwMocaVer = int(local_info[11], 16)
        nwMocaVerVal = f"{(nwMocaVer >> 4) & 0xF}.{nwMocaVer & 0xF}"

        linkStatus = int(local_info[5], 16)
        linkStatusVal = "Up" if linkStatus else "Down"

        # SoC Version
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

        # Chip ID / name
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

        # My MoCA version
        myMocaVer = int(net_info[4], 16)
        myMocaVerVal = f"{(myMocaVer >> 4) & 0xF}.{myMocaVer & 0xF}"

        # Ethernet stats
        txgood = ((int(frame_info[12], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[13], 16)
        txbad = ((int(frame_info[30], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[31], 16)
        txdropped = ((int(frame_info[48], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[49], 16)

        rxgood = ((int(frame_info[66], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[67], 16)
        rxbad = ((int(frame_info[84], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[85], 16)
        rxdropped = ((int(frame_info[102], 16) & 0xFFFFFFFF) * 4294967296) + int(frame_info[103], 16)

        # IP address
        ipAddrInt = int(ip_addr[0], 16)
        ipAddrVal = f"{(ipAddrInt >> 24) & 0xFF}.{(ipAddrInt >> 16) & 0xFF}.{(ipAddrInt >> 8) & 0xFF}.{ipAddrInt & 0xFF}"

        # LOF
        lofVal = int(lof[0], 16)

        # Return final dictionary for sensors
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

    # --------------------------------------------------------------------------------
    # Optional: If you want to gather PHY Rates too, add your get_phy_rates here
    # and call it from the sensor or coordinator code.
    # --------------------------------------------------------------------------------
    # def get_phy_rates(self):
    #     ...
    #     return some_dict_of_phy_rates

"""Helper API calls for GoCoax integration."""
import requests
from requests.auth import HTTPDigestAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global endpoints from your code
ENDPOINTS = {
    'devStatus': '/devStatus.html',
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


def validate_connection(host: str, username: str, password: str) -> bool:
    """
    Attempt to retrieve the devStatus page to confirm credentials are valid.
    Used in config_flow to test connectivity before creating a config entry.
    """
    base_url = f"http://{host}"
    session = requests.Session()
    # Basic auth (uncomment Digest if you need it)
    session.auth = (username, password)
    # session.auth = HTTPDigestAuth(username, password)

    dev_status_url = base_url + ENDPOINTS['devStatus']
    resp = session.get(dev_status_url, verify=False, timeout=5)
    resp.raise_for_status()

    return True


class GoCoaxAPI:
    """
    A Python API for GoCoax MoCA adapters, adapted from your original scripts.
    Provides:
      - retrieve_device_info(): collects all device info
      - display_device_info(): parse raw data -> dictionary of main sensors
      - get_phy_rates(): calculates node-to-node PHY rates
    """

    def __init__(self, host: str, username: str, password: str):
        self._base_url = f"http://{host}"
        self._session = requests.Session()
        self._session.auth = (username, password)
        # For digest:
        # self._session.auth = HTTPDigestAuth(username, password)

        # We store endpoints in an instance attribute if needed
        # or just refer to the global ENDPOINTS dict
        self.endpoints = ENDPOINTS

    # --------------------------------------------------------------------------
    # Basic HTTP helpers (same as your code)
    # --------------------------------------------------------------------------
    def get_csrf_token(self):
        return self._session.cookies.get('csrf_token')

    def post_data(self, action_url, payload_dict=None, referer=None, payload_format='json', debug=False):
        url = self._base_url + action_url
        csrf_token = self.get_csrf_token()

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Connection': 'keep-alive',
            'Origin': self._base_url,
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if referer:
            headers['Referer'] = self._base_url + referer
        else:
            headers['Referer'] = self._base_url + ENDPOINTS['devStatus']

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

        if payload_format == 'json':
            resp = self._session.post(
                url, json=data_to_send, headers=headers, verify=False
            )
        else:
            resp = self._session.post(
                url, data=data_to_send, headers=headers, verify=False
            )

        resp.raise_for_status()

        # When sending form encoded data the response might not be JSON, but
        # all current callers expect JSON. In case the server returns non JSON
        # just return an empty dictionary which matches the previous behaviour
        try:
            return resp.json()
        except ValueError:
            return {}

    def get_data(self, action_url, referer=None, debug=False):
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

    # --------------------------------------------------------------------------
    # retrieve_device_info + display_device_info
    # (Your standard device info scraping and parsing)
    # --------------------------------------------------------------------------
    def retrieve_device_info(self):
        """Collect many device info fields and return as a dict of raw data."""
        dev_status_url = self._base_url + ENDPOINTS['devStatus']
        resp = self._session.get(dev_status_url, verify=False)
        resp.raise_for_status()

        if not self.get_csrf_token():
            raise ValueError("Failed to retrieve CSRF token.")

        device_info = {}

        # localInfo
        local_info = self.post_data(ENDPOINTS['localInfo'])
        device_info['localInfo'] = local_info['data']
        my_node_id = int(device_info['localInfo'][0], 16)

        # ... same pattern for netInfo, macInfo, etc. ...
        net_info = self.post_data(ENDPOINTS['netInfo'], payload_dict={"data": [my_node_id]})
        device_info['netInfo'] = net_info['data']

        mac_info = self.post_data(ENDPOINTS['macInfo'], payload_dict={"data": [my_node_id]})
        device_info['macInfo'] = mac_info['data']

        frame_info = self.post_data(ENDPOINTS['frameInfo'], payload_dict={"data": [0]})
        device_info['frameInfo'] = frame_info['data']

        lof = self.post_data(ENDPOINTS['lof'])
        device_info['lof'] = lof['data']

        ip_addr = self.post_data(ENDPOINTS['ipAddr'])
        device_info['ipAddr'] = ip_addr['data']

        chip_id = self.post_data(ENDPOINTS['ChipID'])
        device_info['chipId'] = chip_id['data']

        gpio = self.post_data(ENDPOINTS['gpio'], payload_dict={"data": [0]})
        device_info['gpio'] = gpio['data']

        miscm25phyinfo = self.post_data(ENDPOINTS['miscm25phyinfo'])
        device_info['miscm25phyinfo'] = miscm25phyinfo['data']

        miscphyinfo = self.post_data(ENDPOINTS['miscphyinfo'])
        device_info['miscphyinfo'] = miscphyinfo['data']

        return device_info

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

    def display_device_info(self, device_info):
        """
        Process raw device info (localInfo, netInfo, etc.) -> dictionary of sensor-friendly values.
        """
        local_info = device_info['localInfo']
        net_info = device_info['netInfo']
        mac_info = device_info['macInfo']
        frame_info = device_info['frameInfo']
        lof = device_info['lof']
        ip_addr = device_info['ipAddr']
        chip_id = device_info['chipId']
        miscphyinfo = device_info['miscphyinfo']
        gpio = device_info['gpio']
        miscm25phyinfo = device_info['miscm25phyinfo']

        # Sample parsing logic from your original script
        nwMocaVer = int(local_info[11], 16)
        nwMocaVerVal = f"{(nwMocaVer >> 4) & 0xF}.{nwMocaVer & 0xF}"

        linkStatus = int(local_info[5], 16)
        linkStatusVal = "Up" if linkStatus else "Down"

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

        chipArray = ["MXL370x", "MXL371x", "UNKNOWN"]
        chipIdInt = int(chip_id[0], 16)
        chipIdIndex = chipIdInt - 0x15
        if chipIdIndex >= len(chipArray):
            chipIdIndex = len(chipArray) - 1
        chipName = chipArray[chipIdIndex]
        socVersionVal = f"{chipName}.{socVersion}"

        hi = int(mac_info[0], 16)
        lo = int(mac_info[1], 16)
        macAddressVal = self.hex2mac(hi, lo)

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

        # IP
        ipAddrInt = int(ip_addr[0], 16)
        ipAddrVal = f"{(ipAddrInt >> 24) & 0xFF}.{(ipAddrInt >> 16) & 0xFF}.{(ipAddrInt >> 8) & 0xFF}.{ipAddrInt & 0xFF}"

        # LOF
        lofVal = int(lof[0], 16)

        # Return as dictionary
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

    # --------------------------------------------------------------------------
    # get_phy_rates: calculates node-to-node rates (your original code, adapted)
    # --------------------------------------------------------------------------
    def get_phy_rates(self, debug=False):
        """
        Gather node-to-node PHY rates, returning a dictionary:
          {
            "nodes": [list of active node IDs],
            "rates": 2D array [id_index][jd_index],
            "gcd_rates": array
          }
        """
        # Constants
        MAX_NUM_NODES = 16
        LDPC_LEN_100MHZ = 3900
        LDPC_LEN_50MHZ = 1200
        FFT_LEN_100MHZ = 512
        FFT_LEN_50MHZ = 256

        # Step 0: Access phyRates.html to init CSRF
        phy_rates_url = self._base_url + ENDPOINTS['phyRates']
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html, */*',
            'Connection': 'keep-alive',
        }
        resp = self._session.get(phy_rates_url, headers=headers, verify=False)
        resp.raise_for_status()

        if not self.get_csrf_token():
            if debug:
                print("Failed to retrieve CSRF token for phyRates.")
            return None

        # Initialize data structures
        rateNper = [[0]*MAX_NUM_NODES for _ in range(MAX_NUM_NODES)]
        rateVlper = [[0]*MAX_NUM_NODES for _ in range(MAX_NUM_NODES)]
        rateGcd = [0]*MAX_NUM_NODES
        netInfo = [None]*MAX_NUM_NODES
        fmrInfo = [None]*MAX_NUM_NODES
        nodeId = []

        # Step 1: localInfo
        local_info_resp = self.post_data(ENDPOINTS['localInfo'], debug=debug)
        LocalInfo = local_info_resp['data']
        my_node_id = int(LocalInfo[0], 16)
        mocaNetVer = int(LocalInfo[11], 16)
        nodeBitMask = int(LocalInfo[12], 16)
        ncNodeID = int(LocalInfo[1], 16) & 0xFF

        # Step 2: netInfo for each node
        for node_id in range(MAX_NUM_NODES):
            currNodeMask = 1 << node_id
            if nodeBitMask & currNodeMask:
                payload_dict = {"data": [node_id]}
                net_info_resp = self.post_data(ENDPOINTS['netInfo'], payload_dict=payload_dict, debug=debug)
                netInfo[node_id] = net_info_resp['data']
                nodeId.append(node_id)
            else:
                netInfo[node_id] = None

        # NC's MoCA version
        ncMocaVer = int(netInfo[ncNodeID][4], 16) & 0xFF

        # Step 3: fmrInfo for each node
        for node_id in nodeId:
            nodeMocaVer = int(netInfo[node_id][4], 16) & 0xFF
            mocaVer = min(ncMocaVer, nodeMocaVer)
            finalVer = 1 if mocaVer < 0x20 else 2
            currNodeMask = 1 << node_id

            payload_dict = {"data": [currNodeMask, finalVer]}
            fmr_info_resp = self.post_data(
                ENDPOINTS['fmrInfo'],
                payload_dict=payload_dict,
                payload_format='json',
                debug=debug
            )
            fmrInfo[node_id] = fmr_info_resp['data']

        # Step 4: Calculate PHY rates
        for id_index, id_val in enumerate(nodeId):
            entryNodePayloadVer = min(int(netInfo[id_val][4], 16) & 0xFF, ncMocaVer)
            readIndx = 10
            alignmentFlag = True
            rateGcd[id_index] = 0
            mocaNodeVer = int(netInfo[id_val][4], 16) & 0xFF

            for jd_index, jd_val in enumerate(nodeId):
                node_jd_mocaNodeVer = int(netInfo[jd_val][4], 16) & 0xFF
                if ncMocaVer < 0x20:
                    fmrPayloadVer = min(entryNodePayloadVer, node_jd_mocaNodeVer)
                else:
                    fmrPayloadVer = mocaNodeVer

                fmr_data = fmrInfo[id_val]
                try:
                    if fmrPayloadVer in (0x20, 0x25):
                        # MoCA 2.x
                        if alignmentFlag:
                            val1 = int(fmr_data[readIndx], 16)
                            gapNper = (val1 >> 24) & 0xFF
                            gapVLper = (val1 >> 16) & 0xFF
                            ofdmbNper = val1 & 0xFFFF
                            val2 = int(fmr_data[readIndx+1], 16)
                            ofdmbVLper = (val2 >> 16) & 0xFFFF
                            readIndx += 1
                        else:
                            val1 = int(fmr_data[readIndx], 16)
                            gapNper = (val1 >> 8) & 0xFF
                            gapVLper = val1 & 0xFF
                            val2 = int(fmr_data[readIndx+1], 16)
                            ofdmbNper = (val2 >> 16) & 0xFFFF
                            ofdmbVLper = val2 & 0xFFFF
                            readIndx += 2
                    else:
                        # MoCA 1.x
                        gapVLper = 0
                        ofdmbVLper = 0
                        val = int(fmr_data[readIndx], 16)
                        if alignmentFlag:
                            gapNper = (val & 0xF8000000) >> 27
                            ofdmbNper = (val & 0x07FF0000) >> 16
                        else:
                            gapNper = (val & 0x0000F800) >> 11
                            ofdmbNper = val & 0x000007FF
                            readIndx += 1

                    alignmentFlag = not alignmentFlag

                    # Calculate PHY rates
                    if gapVLper == 0:
                        rateVlper[id_index][jd_index] = 0
                    else:
                        rateVlper[id_index][jd_index] = (
                                                                LDPC_LEN_100MHZ * ofdmbVLper
                                                        ) // (
                                                                (FFT_LEN_100MHZ + ((gapVLper + 10) * 2)) * 46
                                                        )

                    if gapNper == 0:
                        rateNper[id_index][jd_index] = 0
                    elif gapVLper == 0 and fmrPayloadVer == 0x20:
                        # MoCA 2.x but 50MHz?
                        rateNper[id_index][jd_index] = (
                                                               LDPC_LEN_50MHZ * ofdmbNper
                                                       ) // (
                                                               (FFT_LEN_50MHZ + (gapNper * 2 + 10)) * 26
                                                       )
                    else:
                        # MoCA 2.x 100MHz?
                        rateNper[id_index][jd_index] = (
                                                               LDPC_LEN_100MHZ * ofdmbNper
                                                       ) // (
                                                               (FFT_LEN_100MHZ + ((gapNper + 10) * 2)) * 46
                                                       )

                    # Calculate GCD
                    if id_val == jd_val:
                        if (mocaNodeVer & 0xF0) == 0x10:
                            # MoCA 1.x
                            gapGcd = gapNper
                            ofdmbGcd = ofdmbNper
                            rateGcd[id_index] = (
                                                        LDPC_LEN_50MHZ * ofdmbGcd
                                                ) // (
                                                        (FFT_LEN_50MHZ + (gapGcd * 2 + 10)) * 26
                                                )
                        elif (mocaNodeVer & 0xF0) == 0x20:
                            # MoCA 2.x
                            gapGcd = gapNper
                            ofdmbGcd = ofdmbNper
                            rateGcd[id_index] = (
                                                        LDPC_LEN_100MHZ * ofdmbGcd
                                                ) // (
                                                        (FFT_LEN_100MHZ + ((gapGcd + 10) * 2)) * 46
                                                )
                except Exception as e:
                    if debug:
                        print(f"Error parsing FMR data for node {id_val}: {e}")
                    rateNper[id_index][jd_index] = 0
                    rateVlper[id_index][jd_index] = 0

        # Return the structure needed
        return {
            "nodes": nodeId,
            "rates": rateNper,
            "gcd_rates": rateGcd,
        }

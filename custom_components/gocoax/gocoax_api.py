"""Helper API calls for GoCoax integration."""
import requests
from requests.auth import HTTPDigestAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def validate_connection(host: str, username: str, password: str) -> bool:
    """Attempt to retrieve the devStatus page to confirm credentials are valid."""
    base_url = f"http://{host}"
    session = requests.Session()
    # For Basic Auth:
    session.auth = (username, password)
    # If your device actually needs Digest Auth, do:
    # session.auth = HTTPDigestAuth(username, password)
    dev_status_url = base_url + "/devStatus.html"

    resp = session.get(dev_status_url, verify=False, timeout=5)
    resp.raise_for_status()

    # If we got here, we presumably have the right credentials
    return True

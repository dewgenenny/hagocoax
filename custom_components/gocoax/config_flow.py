import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from .gocoax_api import validate_connection

_LOGGER = logging.getLogger(__name__)

class GoCoaxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoCoax."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step (user entering host/username/password)."""
        errors = {}

        if user_input is not None:
            # Extract the user input
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Try to connect
            connection_ok = False
            try:
                connection_ok = await self._async_validate_connection(
                    host, username, password
                )
            except Exception as exc:
                _LOGGER.exception("Unexpected exception: %s", exc)
                errors["base"] = "unknown"

            if connection_ok:
                # If there's already a config entry for this host, abort to avoid duplicates
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                # Create and store the config entry
                return self.async_create_entry(
                    title=f"GoCoax ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
            else:
                errors["base"] = "cannot_connect"

        # Show the form (on first load or if connection fails)
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _async_validate_connection(self, host, username, password) -> bool:
        """Check if the provided host/credentials are valid."""
        # Run the test in the executor thread, so we don't block event loop
        return await self.hass.async_add_executor_job(
            validate_connection, host, username, password
        )


def validate_connection(host: str, username: str, password: str) -> bool:
    """Synchronous helper that uses GoCoaxAPI to attempt a simple request."""
    # Create the API instance
    api = GoCoaxAPI(host, username, password)

    # For a quick check, we can just do something like devStatus.html.
    # If it raises an HTTP error => invalid credentials or offline device
    dev_status_url = api._base_url + api.endpoints['devStatus']  # or some small request
    response = api._session.get(dev_status_url, verify=False, timeout=5)
    response.raise_for_status()

    # If we got here with no exception, we assume it’s valid
    return True

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD
# Import validate_connection from gocoax_api.py
from .gocoax_api import validate_connection

_LOGGER = logging.getLogger(__name__)


class GoCoaxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoCoax."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """
        The first (and only) step in our config flow.
        Asks user for host/username/password, tests them,
        and creates a config entry if valid.
        """
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Attempt to connect / validate
            connection_ok = False
            try:
                connection_ok = await self._async_validate_connection(
                    host, username, password
                )
            except Exception as exc:
                _LOGGER.exception("Unexpected error validating connection: %s", exc)
                errors["base"] = "unknown"

            if connection_ok:
                # Use host as the unique_id so we don't add duplicates
                await self.async_set_unique_id(host.lower())
                self._abort_if_unique_id_configured()

                # Create a new config entry
                return self.async_create_entry(
                    title=f"GoCoax ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
            else:
                if "base" not in errors:
                    errors["base"] = "cannot_connect"

        # If no user_input yet, or connection failed, show the form again
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

    async def _async_validate_connection(self, host: str, username: str, password: str) -> bool:
        """
        Calls our synchronous validate_connection in a thread,
        so we don't block the event loop.
        """
        return await self.hass.async_add_executor_job(
            validate_connection, host, username, password
        )

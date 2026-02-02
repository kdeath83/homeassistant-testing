"""Config flow for Remote Calendar integration."""

from http import HTTPStatus
import logging
from typing import Any

from httpx import AsyncClient, HTTPError, InvalidURL, Response, TimeoutException
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.helpers.httpx_client import get_async_client

from .client import get_calendar
from .const import CONF_CALENDAR_NAME, DOMAIN
from .ics import InvalidIcsException, parse_calendar

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CALENDAR_NAME): str,
        vol.Required(CONF_URL): str,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)

STEP_AUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _supports_basic_auth(headers: dict[str, str]) -> bool:
    """Check if server supports HTTP Basic Authentication."""
    www_authenticate = headers.get("www-authenticate", "").lower()
    return "basic" in www_authenticate


class RemoteCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Remote Calendar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.data: dict[str, Any] = {}

    async def _fetch_calendar(
        self,
        client: AsyncClient,
        url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> tuple[str | None, Response | None]:
        """Fetch and validate calendar, returning (error_key, response) tuple."""
        try:
            res = await get_calendar(client, url, username, password)
        except TimeoutException as err:
            _LOGGER.debug("Timeout: %s", str(err) or type(err).__name__)
            return ("timeout_connect", None)
        except (HTTPError, InvalidURL) as err:
            _LOGGER.debug("Error: %s", str(err) or type(err).__name__)
            return ("cannot_connect", None)

        # Check for auth errors before raise_for_status
        if res.status_code == HTTPStatus.UNAUTHORIZED:
            return ("unauthorized", res)
        if res.status_code == HTTPStatus.FORBIDDEN:
            return ("forbidden", res)

        # Check for other HTTP errors
        try:
            res.raise_for_status()
        except HTTPError:
            return ("cannot_connect", res)

        # Validate ICS content
        try:
            await parse_calendar(self.hass, res.text)
        except InvalidIcsException:
            return ("invalid_ics_file", res)

        return (None, res)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict = {}
        _LOGGER.debug("User input: %s", user_input)

        self._async_abort_entries_match(
            {CONF_CALENDAR_NAME: user_input[CONF_CALENDAR_NAME]}
        )
        if user_input[CONF_URL].startswith("webcal://"):
            user_input[CONF_URL] = user_input[CONF_URL].replace(
                "webcal://", "https://", 1
            )
        self._async_abort_entries_match({CONF_URL: user_input[CONF_URL]})

        client = get_async_client(self.hass, verify_ssl=user_input[CONF_VERIFY_SSL])

        # First, check if URL requires authentication
        try:
            res = await get_calendar(client, user_input[CONF_URL])
        except TimeoutException as err:
            _LOGGER.debug("Timeout: %s", str(err) or type(err).__name__)
            errors["base"] = "timeout_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, user_input
                ),
                errors=errors,
            )
        except (HTTPError, InvalidURL) as err:
            _LOGGER.debug("Error: %s", str(err) or type(err).__name__)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, user_input
                ),
                errors=errors,
            )

        # Handle authentication required
        if res.status_code == HTTPStatus.UNAUTHORIZED:
            if _supports_basic_auth(dict(res.headers)):
                self.data = user_input
                return await self.async_step_auth()
            # Server doesn't support Basic Auth
            errors["base"] = "unauthorized"
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, user_input
                ),
                errors=errors,
            )

        # Handle forbidden - abort, changing URL won't help
        if res.status_code == HTTPStatus.FORBIDDEN:
            return self.async_abort(reason="forbidden")

        # Handle other HTTP errors
        try:
            res.raise_for_status()
        except HTTPError:
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, user_input
                ),
                errors=errors,
            )

        # Validate ICS content
        try:
            await parse_calendar(self.hass, res.text)
        except InvalidIcsException:
            errors["base"] = "invalid_ics_file"
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, user_input
                ),
                errors=errors,
            )

        return self.async_create_entry(
            title=user_input[CONF_CALENDAR_NAME], data=user_input
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the authentication step."""
        if user_input is None:
            return self.async_show_form(
                step_id="auth",
                data_schema=STEP_AUTH_DATA_SCHEMA,
            )

        client = get_async_client(
            self.hass, verify_ssl=self.data.get(CONF_VERIFY_SSL, True)
        )

        error, _ = await self._fetch_calendar(
            client,
            self.data[CONF_URL],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )

        if error:
            # 403 after providing credentials = access denied, abort
            if error == "forbidden":
                return self.async_abort(reason="forbidden")

            return self.async_show_form(
                step_id="auth",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_AUTH_DATA_SCHEMA, user_input
                ),
                errors={"base": error},
            )

        # Success - combine stored data with auth credentials
        entry_data = {
            **self.data,
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_PASSWORD: user_input[CONF_PASSWORD],
        }
        return self.async_create_entry(
            title=self.data[CONF_CALENDAR_NAME], data=entry_data
        )

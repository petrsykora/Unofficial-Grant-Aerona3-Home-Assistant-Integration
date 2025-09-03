"""Config flow for Grant Aerona3 Heat Pump integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

INTEGRATION_VERSION = "1.1.1"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    slave_id = data[CONF_SLAVE_ID]

    # Test the connection
    client = ModbusTcpClient(host=host, port=port, timeout=5)

    try:
        if not await hass.async_add_executor_job(client.connect):
            raise CannotConnect("Failed to connect to heat pump")

        # Try to read a register to verify communication
        result = await hass.async_add_executor_job(
            lambda: client.read_input_registers(address=0, count=1, slave=slave_id)
        )

        if result.isError():
            raise CannotConnect("Failed to read from heat pump - check Slave ID")

        _LOGGER.info("Successfully connected to Grant Aerona3 at %s:%s", host, port)

    except ModbusException as err:
        _LOGGER.error("Modbus error connecting to %s:%s - %s", host, port, err)
        raise CannotConnect(f"Modbus communication error: {err}") from err
    except Exception as err:
        _LOGGER.error("Unexpected error connecting to %s:%s - %s", host, port, err)
        raise CannotConnect(f"Unexpected error: {err}") from err
    finally:
        await hass.async_add_executor_job(client.close)

    # Return info that you want to store in the config entry.
    return {
        "title": f"ASHP Grant Aerona3 ({host})",
        "host": host,
        "port": port,
        "slave_id": slave_id,
        "scan_interval": data[CONF_SCAN_INTERVAL],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grant Aerona3 Heat Pump."""

    VERSION = 1  # Home Assistant expects an integer here

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "integration_name": "Grant Aerona3 Heat Pump (ASHP)",
                "version": INTEGRATION_VERSION,
                "features": "All entities will have 'ashp_' prefixes for better organisation"
            }
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Grant Aerona3 options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                    vol.Optional(
                        "flow_rate_lpm",
                        default=self.config_entry.options.get(
                            "flow_rate_lpm",
                            self.config_entry.data.get("flow_rate_lpm", 30.0)
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=100.0)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
# custom_components/grant_aerona3/options_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL

DOMAIN = "grant_aerona3"
DEFAULT_SCAN_INTERVAL = 30  # seconds
CONF_FLOW_RATE_LPM = "flow_rate_lpm"
DEFAULT_FLOW_RATE_LPM = 34  # L/min

class GrantAerona3OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Grant Aerona3 options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    )
                ): vol.All(int, vol.Range(min=5, max=300)),
                vol.Optional(
                    CONF_FLOW_RATE_LPM,
                    default=self.config_entry.options.get(
                        CONF_FLOW_RATE_LPM,
                        self.config_entry.data.get(CONF_FLOW_RATE_LPM, DEFAULT_FLOW_RATE_LPM)
                    )
                ): vol.All(float, vol.Range(min=1, max=100)),
            }),
            description_placeholders={
                "scan_interval": "How often to poll the heat pump (seconds)",
                "flow_rate_lpm": "Flow rate in litres per minute (L/min)",
            }
        )

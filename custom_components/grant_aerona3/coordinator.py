# custom_components/grant_aerona3/coordinator.py

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    COIL_REGISTER_MAP,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

class GrantAerona3Coordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator for Grant Aerona3 Heat Pump."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.slave_id = entry.data[CONF_SLAVE_ID]
        # Use options if present, else data, else default
        scan_interval = (
            entry.options.get(CONF_SCAN_INTERVAL)
            if hasattr(entry, "options") and entry.options.get(CONF_SCAN_INTERVAL) is not None
            else entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        flow_rate_lpm = (
            entry.options.get("flow_rate_lpm")
            if hasattr(entry, "options") and entry.options.get("flow_rate_lpm") is not None
            else entry.data.get("flow_rate_lpm", 10)
        )
        self.flow_rate_lpm = flow_rate_lpm

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=10,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(self._fetch_data(), timeout=30.0)
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to ASHP at {self.host}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ASHP: {err}") from err

    async def _fetch_data(self) -> Dict[str, Any]:
        data = {
            "input_registers": {},
            "holding_registers": {},
            "coil_registers": {},
            "last_update": asyncio.get_running_loop().time(),
        }
        try:
            connected = await self.hass.async_add_executor_job(self._client.connect)
            if not connected:
                raise UpdateFailed(f"Failed to connect to ASHP at {self.host}:{self.port}")
            data["input_registers"] = await self._read_input_registers()
            data["holding_registers"] = await self._read_holding_registers()
            data["coil_registers"] = await self._read_coil_registers()
            data["calculated"] = self._calculate_derived_values(
                data["input_registers"], data["holding_registers"]
            )
        except ModbusException as err:
            _LOGGER.error("Modbus error: %s", err)
            raise UpdateFailed(f"Modbus communication error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            try:
                await self.hass.async_add_executor_job(self._client.close)
            except Exception:
                pass
        return data

    async def _read_input_registers(self) -> Dict[int, float]:
        input_data = {}
        chunk_size = 20
        register_ids = list(INPUT_REGISTER_MAP.keys())
        for i in range(0, len(register_ids), chunk_size):
            chunk = register_ids[i:i + chunk_size]
            if not chunk:
                continue
            start_reg = min(chunk)
            end_reg = max(chunk)
            count = end_reg - start_reg + 1
            try:
                result = await self.hass.async_add_executor_job(
                    lambda start_reg=start_reg, count=count: self._client.read_input_registers(start_reg, count=count, slave=self.slave_id)
                )
                if not result.isError():
                    for j, reg_id in enumerate(range(start_reg, end_reg + 1)):
                        if reg_id in INPUT_REGISTER_MAP and j < len(result.registers):
                             raw_value = result.registers[j]
                             # Handle signed 16-bit values
                             if raw_value > 32767:
                                raw_value = raw_value - 65536
                             input_data[reg_id] = raw_value
                else:
                    _LOGGER.warning("Error reading input registers %d-%d: %s", start_reg, end_reg, result)
            except Exception as err:
                _LOGGER.warning("Failed to read input registers %d-%d: %s", start_reg, end_reg, err)
        return input_data

    async def _read_holding_registers(self) -> Dict[int, float]:
        holding_data = {}
        chunk_size = 20
        register_ids = list(HOLDING_REGISTER_MAP.keys())
        for i in range(0, len(register_ids), chunk_size):
            chunk = register_ids[i:i + chunk_size]
            if not chunk:
                continue
            start_reg = min(chunk)
            end_reg = max(chunk)
            count = end_reg - start_reg + 1
            try:
                result = await self.hass.async_add_executor_job(
                    lambda start_reg=start_reg, count=count: self._client.read_holding_registers(start_reg, count=count, slave=self.slave_id)
                )
                if not result.isError():
                    for j, reg_id in enumerate(range(start_reg, end_reg + 1)):
                        if reg_id in HOLDING_REGISTER_MAP and j < len(result.registers):
                            raw_value = result.registers[j]
                            # Handle signed 16-bit values
                            if raw_value > 32767:
                                raw_value = raw_value - 65536
                            holding_data[reg_id] = raw_value
                else:
                    _LOGGER.warning("Error reading holding registers %d-%d: %s", start_reg, end_reg, result)
            except Exception as err:
                _LOGGER.warning("Failed to read holding registers %d-%d: %s", start_reg, end_reg, err)
        return holding_data

    async def _read_coil_registers(self) -> Dict[int, bool]:
        coil_data = {}
        chunk_size = 20
        register_ids = list(COIL_REGISTER_MAP.keys())
        for i in range(0, len(register_ids), chunk_size):
            chunk = register_ids[i:i + chunk_size]
            if not chunk:
                continue
            start_reg = min(chunk)
            end_reg = max(chunk)
            count = end_reg - start_reg + 1
            try:
                result = await self.hass.async_add_executor_job(
                    lambda start_reg=start_reg, count=count: self._client.read_coils(start_reg, count=count, slave=self.slave_id)
                )
                if not result.isError():
                    for j, reg_id in enumerate(range(start_reg, end_reg + 1)):
                        if reg_id in COIL_REGISTER_MAP and j < len(result.bits):
                            coil_data[reg_id] = result.bits[j]
                else:
                    _LOGGER.warning("Error reading coil registers %d-%d: %s", start_reg, end_reg, result)
            except Exception as err:
                _LOGGER.warning("Failed to read coil registers %d-%d: %s", start_reg, end_reg, err)
        return coil_data

    def _calculate_derived_values(self, input_data: Dict[int, float], holding_data: Dict[int, float]) -> Dict[str, Any]:
        calculated = {}
        try:
            flow_temp = input_data.get(9)  # Outgoing Water Temperature (°C)
            return_temp = input_data.get(0)  # Return Water Temperature (°C)
            power_w = input_data.get(3, 0) * 100  # Power in W (register 3, scale 100)
            flow_rate_lph = self.flow_rate_lpm * 60

            if (
                flow_temp is not None
                and return_temp is not None
                and power_w > 0
                and flow_rate_lph > 0
            ):
                delta_t = flow_temp - return_temp
                heat_output_w = flow_rate_lph * 1.16 * delta_t
                cop = heat_output_w / power_w
                calculated["cop"] = round(cop, 2)
                calculated["heat_output_w"] = round(heat_output_w, 1)
                calculated["delta_t"] = round(delta_t, 2)
        except Exception as err:
            _LOGGER.warning("Error calculating derived values: %s", err)
        return calculated

    async def async_write_register(self, register: int, value: int) -> bool:
        try:
            connected = await self.hass.async_add_executor_job(self._client.connect)
            if not connected:
                _LOGGER.error("Failed to connect for writing register %d", register)
                return False
            result = await self.hass.async_add_executor_job(
                lambda register=register, value=value: self._client.write_register(register, value, slave=self.slave_id)
            )
            if result.isError():
                _LOGGER.error("Error writing register %d: %s", register, result)
                return False
            _LOGGER.info("Successfully wrote value %d to register %d", value, register)
            await self.async_request_refresh()
            return True
        except Exception as err:
            _LOGGER.error("Failed to write register %d: %s", register, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(self._client.close)
            except Exception:
                pass

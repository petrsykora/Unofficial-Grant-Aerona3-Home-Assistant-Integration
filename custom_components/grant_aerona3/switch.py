"""Switch platform for Grant Aerona3 Heat Pump with ashp_ prefixes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, MANUFACTURER, MODEL, HOLDING_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)

def get_scale(register_id: int) -> float:
    return HOLDING_REGISTER_MAP.get(register_id, {}).get("scale", 1)

class GrantAerona3BaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for Grant Aerona3 switch entities."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "2.0.0",
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs: Any) -> None:
        if hasattr(self, '_register_id') and hasattr(self, '_on_value'):
            scale = get_scale(self._register_id)
            value = int(self._on_value / scale)
            success = await self.coordinator.async_write_register(self._register_id, value)
            if success:
                _LOGGER.info("Successfully turned on %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if hasattr(self, '_register_id') and hasattr(self, '_off_value'):
            scale = get_scale(self._register_id)
            value = int(self._off_value / scale)
            success = await self.coordinator.async_write_register(self._register_id, value)
            if success:
                _LOGGER.info("Successfully turned off %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn off %s", self._attr_name)

class GrantAerona3DHWPrioritySwitch(GrantAerona3BaseSwitch):
    def __init__(self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Priority"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_priority"
        self._attr_icon = "mdi:water-boiler"
        self._attr_entity_category = EntityCategory.CONFIG
        self._register_id = 26
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        return mode > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        priority_descriptions = {
            0: "DHW is unavailable",
            1: "DHW priority over space heating",
            2: "Space heating priority over DHW"
        }
        return {
            "priority_mode": priority_descriptions.get(mode, "Unknown"),
            "register_value": mode,
        }

class GrantAerona3DHWConfigurationSwitch(GrantAerona3BaseSwitch):
    def __init__(self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Heat Pump Only Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_hp_only_mode"
        self._attr_icon = "mdi:heat-pump"
        self._attr_entity_category = EntityCategory.CONFIG
        self._register_id = 27
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)
        return mode == 1

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)
        config_descriptions = {
            0: "Heat pump + Heater",
            1: "Heat pump only",
            2: "Heater only"
        }
        return {
            "dhw_configuration": config_descriptions.get(mode, "Unknown"),
            "register_value": mode,
        }

class GrantAerona3BackupHeaterSwitch(GrantAerona3BaseSwitch):
    def __init__(self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Backup Heater Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_backup_heater_enable"
        self._attr_icon = "mdi:heating-coil"
        self._attr_entity_category = EntityCategory.CONFIG
        self._register_id = 71
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        return mode > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        heater_modes = {
            0: "Disabled",
            1: "Replacement mode",
            2: "Emergency mode",
            3: "Supplementary mode"
        }
        return {
            "backup_heater_mode": heater_modes.get(mode, "Unknown"),
            "register_value": mode,
        }

class GrantAerona3FrostProtectionSwitch(GrantAerona3BaseSwitch):
    def __init__(self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_protection"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:snowflake-alert"
        self._attr_entity_category = EntityCategory.CONFIG
        self._register_id = 81
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        return mode > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        protection_modes = {
            0: "Disabled",
            1: "Enabled during Start-up",
            2: "Enabled during Defrost",
            3: "Enabled during Start-up and Defrost"
        }
        return {
            "frost_protection_mode": protection_modes.get(mode, "Unknown"),
            "register_value": mode,
        }

# Add more switch classes here as needed, following the same pattern.

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        GrantAerona3DHWPrioritySwitch(coordinator, config_entry),
        GrantAerona3DHWConfigurationSwitch(coordinator, config_entry),
        GrantAerona3BackupHeaterSwitch(coordinator, config_entry),
        GrantAerona3FrostProtectionSwitch(coordinator, config_entry),
        # Add other switch classes here...
    ]
    _LOGGER.info("Creating %d ASHP switch entities", len(entities))
    async_add_entities(entities)

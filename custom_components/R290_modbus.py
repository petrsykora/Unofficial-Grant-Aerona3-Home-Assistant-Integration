#!/usr/bin/env python3
"""
Grant Aerona3 R290 Modbus Register Discovery Tool
Systematically scans modbus registers to identify active ones
"""

import time
import json
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import argparse

class ModbusRegisterScanner:
    def __init__(self, host, port=502, unit_id=1):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.client = None
        self.results = {
            'scan_info': {
                'timestamp': datetime.now().isoformat(),
                'host': host,
                'port': port,
                'unit_id': unit_id
            },
            'holding_registers': {},
            'input_registers': {},
            'coils': {},
            'discrete_inputs': {}
        }
    
    def connect(self):
        """Connect to the modbus device"""
        try:
            self.client = ModbusTcpClient(self.host, port=self.port)
            if self.client.connect():
                print(f"✅ Connected to {self.host}:{self.port}")
                return True
            else:
                print(f"❌ Failed to connect to {self.host}:{self.port}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def scan_holding_registers(self, start=0, end=1000, batch_size=10):
        """Scan holding registers in batches"""
        print(f"\n🔍 Scanning Holding Registers {start}-{end}")

        for addr in range(start, end + 1, batch_size):
            try:
                # Read batch of registers
                count = min(batch_size, end - addr + 1)
                result = self.client.read_holding_registers(addr, count=count, device_id=self.unit_id)

                if not result.isError():
                    for i, value in enumerate(result.registers):
                        reg_addr = addr + i
                        if value != 0:  # Only store non-zero values
                            self.results['holding_registers'][reg_addr] = {
                                'value': value,
                                'hex': f"0x{value:04X}",
                                'signed': value if value < 32768 else value - 65536,
                                'float_interpretation': self._try_float_conversion(value)
                            }
                            print(f"  📍 HR{reg_addr}: {value} (0x{value:04X})")

                time.sleep(0.1)  # Be nice to the device

            except Exception as e:
                print(f"  ⚠️  Error reading HR{addr}: {e}")

    def scan_input_registers(self, start=0, end=1000, batch_size=10):
        """Scan input registers in batches"""
        print(f"\n🔍 Scanning Input Registers {start}-{end}")

        for addr in range(start, end + 1, batch_size):
            try:
                count = min(batch_size, end - addr + 1)
                result = self.client.read_input_registers(addr, count=count, device_id=self.unit_id)

                if not result.isError():
                    for i, value in enumerate(result.registers):
                        reg_addr = addr + i
                        if value != 0:
                            self.results['input_registers'][reg_addr] = {
                                'value': value,
                                'hex': f"0x{value:04X}",
                                'signed': value if value < 32768 else value - 65536,
                                'float_interpretation': self._try_float_conversion(value)
                            }
                            print(f"  📍 IR{reg_addr}: {value} (0x{value:04X})")

                time.sleep(0.1)

            except Exception as e:
                print(f"  ⚠️  Error reading IR{addr}: {e}")

    def scan_coils(self, start=0, end=100):
        """Scan coils (discrete outputs)"""
        print(f"\n🔍 Scanning Coils {start}-{end}")

        try:
            count = end - start + 1
            result = self.client.read_coils(start, count=count, device_id=self.unit_id)

            if not result.isError():
                for i, value in enumerate(result.bits):
                    if value:  # Only store active coils
                        coil_addr = start + i
                        self.results['coils'][coil_addr] = True
                        print(f"  📍 Coil{coil_addr}: {value}")
        except Exception as e:
            print(f"  ⚠️  Error reading coils: {e}")

    def scan_discrete_inputs(self, start=0, end=100):
        """Scan discrete inputs"""
        print(f"\n🔍 Scanning Discrete Inputs {start}-{end}")

        try:
            count = end - start + 1
            result = self.client.read_discrete_inputs(start, count=count, device_id=self.unit_id)

            if not result.isError():
                for i, value in enumerate(result.bits):
                    if value:  # Only store active inputs
                        input_addr = start + i
                        self.results['discrete_inputs'][input_addr] = True
                        print(f"  📍 DI{input_addr}: {value}")
        except Exception as e:
            print(f"  ⚠️  Error reading discrete inputs: {e}")

        try:
            count = end - start + 1
            result = self.client.read_discrete_inputs(start, count=count, device_id=self.unit_id)
            if not result.isError():
                for i, value in enumerate(result.bits[:end-start+1]):
                    if value:
                        addr = start + i
                        self.results['discrete_inputs'][addr] = value
                        print(f"  📍 DI{addr}: {value}")
        except Exception as e:
            print(f"  ⚠️  Error reading discrete inputs: {e}")
    
    def _try_float_conversion(self, value):
        """Try to interpret value as temperature/pressure etc"""
        interpretations = {}
        
        # Common HVAC interpretations
        interpretations['temp_c_div10'] = value / 10.0
        interpretations['temp_c_div100'] = value / 100.0
        interpretations['pressure_bar_div10'] = value / 10.0
        interpretations['percentage'] = value / 100.0 if value <= 10000 else None
        
        return interpretations
    
    def monitor_changes(self, registers_to_monitor, duration=60):
        """Monitor specific registers for changes over time"""
        print(f"\n👀 Monitoring registers for {duration} seconds...")

        start_time = time.time()
        previous_values = {}

        while time.time() - start_time < duration:
            for reg_type, addresses in registers_to_monitor.items():
                for addr in addresses:
                    try:
                        if reg_type == 'holding':
                            result = self.client.read_holding_registers(addr, count=1, device_id=self.unit_id)
                        elif reg_type == 'input':
                            result = self.client.read_input_registers(addr, count=1, device_id=self.unit_id)

                        if not result.isError():
                            current_value = result.registers[0]
                            key = f"{reg_type}_{addr}"

                            if key in previous_values and previous_values[key] != current_value:
                                print(f"  🔄 {reg_type.upper()}{addr}: {previous_values[key]} → {current_value}")

                            previous_values[key] = current_value

                    except Exception as e:
                        print(f"  ⚠️  Error monitoring {reg_type}{addr}: {e}")

            time.sleep(2)
    
    def save_results(self, filename=None):
        """Save scan results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"r290_modbus_scan_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to {filename}")
        return filename
    
    def disconnect(self):
        """Disconnect from modbus device"""
        if self.client:
            self.client.close()
            print("🔌 Disconnected")

def main():
    parser = argparse.ArgumentParser(description='Grant Aerona3 R290 Modbus Register Scanner')
    parser.add_argument('host', help='IP address of the heat pump')
    parser.add_argument('--port', type=int, default=502, help='Modbus TCP port (default: 502)')
    parser.add_argument('--unit', type=int, default=1, help='Modbus unit ID (default: 1)')
    parser.add_argument('--hr-start', type=int, default=0, help='Holding registers start address')
    parser.add_argument('--hr-end', type=int, default=1000, help='Holding registers end address')
    parser.add_argument('--ir-start', type=int, default=0, help='Input registers start address')
    parser.add_argument('--ir-end', type=int, default=1000, help='Input registers end address')
    parser.add_argument('--monitor', action='store_true', help='Monitor for register changes')
    
    args = parser.parse_args()
    
    scanner = ModbusRegisterScanner(args.host, args.port, args.unit)
    
    if not scanner.connect():
        return
    
    try:
        # Scan holding registers
        scanner.scan_holding_registers(args.hr_start, args.hr_end)
        
        # Scan input registers  
        scanner.scan_input_registers(args.ir_start, args.ir_end)
        
        # Scan coils and discrete inputs
        scanner.scan_coils()
        scanner.scan_discrete_inputs()
        
        # Save initial scan
        filename = scanner.save_results()
        
        # Optional monitoring phase
        if args.monitor:
            # Monitor registers that had non-zero values
            registers_to_monitor = {
                'holding': list(scanner.results['holding_registers'].keys()),
                'input': list(scanner.results['input_registers'].keys())
            }
            
            if registers_to_monitor['holding'] or registers_to_monitor['input']:
                scanner.monitor_changes(registers_to_monitor, duration=120)
                scanner.save_results(filename.replace('.json', '_with_monitoring.json'))
        
        print(f"\n✅ Scan complete! Found:")
        print(f"   • {len(scanner.results['holding_registers'])} active holding registers")
        print(f"   • {len(scanner.results['input_registers'])} active input registers")
        print(f"   • {len(scanner.results['coils'])} active coils")
        print(f"   • {len(scanner.results['discrete_inputs'])} active discrete inputs")
        
    finally:
        scanner.disconnect()

if __name__ == "__main__":
    main()
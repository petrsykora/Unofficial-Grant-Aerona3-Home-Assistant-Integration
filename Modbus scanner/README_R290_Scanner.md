# Grant R290 ASHP Modbus Register Scanner

A comprehensive Python tool for discovering and monitoring Modbus registers on Grant Aerona3 R290 Air Source Heat Pumps (ASHP) Or any other modbus device. This scanner helps identify available data points, sensor readings, and control registers for integration with home automation systems like Home Assistant.

## 🚀 Features

- **Complete Register Discovery**: Scans holding registers, input registers, coils, and discrete inputs
- **Multiple Data Interpretations**: Shows values as raw integers, hexadecimal, signed values, and potential float conversions
- **Live Monitoring**: Track register changes over time to identify dynamic data
- **Batch Processing**: Configurable batch sizes to avoid overwhelming the heat pump
- **JSON Export**: Saves results with timestamps for analysis
- **Error Handling**: Graceful handling of connection issues and timeouts
- **Flexible Configuration**: Customizable register ranges and scan parameters

## 📋 Prerequisites

- Python 3.6 or higher
- Network access to your Grant R290 ASHP
- Heat pump configured for Modbus TCP communication

## 🔧 Installation

1. **Clone or download** the `R290_modbus.py` script

2. **Install required dependencies**:
   ```bash
   pip install pymodbus
   ```

   Or using a virtual environment (recommended):
   ```bash
   python3 -m venv modbus_env
   source modbus_env/bin/activate  # On Windows: modbus_env\Scripts\activate
   pip install pymodbus
   ```

## 🎯 Usage

### Basic Scan
Scan your heat pump with default settings (change the IP to address t the IP address of your ASHP):
```bash
python3 R290_modbus.py 192.168.1.100
```

### Custom Register Ranges
Specify custom ranges for different register types:
```bash
python3 R290_modbus.py 192.168.1.100 --hr-start 0 --hr-end 100 --ir-start 0 --ir-end 50
```

### Monitor for Changes
Monitor specific registers to identify live data:
```bash
python3 R290_modbus.py 192.168.1.100 --monitor --hr-start 0 --hr-end 50
```

### Full Command Options
```bash
python3 R290_modbus.py [IP_ADDRESS] [OPTIONS]

Positional Arguments:
  IP_ADDRESS           IP address of your Grant R290 heat pump

Optional Arguments:
  -h, --help           Show help message
  --port PORT          Modbus TCP port (default: 502)
  --unit UNIT          Modbus unit ID (default: 1)
  --hr-start HR_START  Holding registers start address (default: 0)
  --hr-end HR_END      Holding registers end address (default: 1000)
  --ir-start IR_START  Input registers start address (default: 0)
  --ir-end IR_END      Input registers end address (default: 1000)
  --monitor            Enable change monitoring mode
```

## 📊 Understanding the Output

### Register Types

1. **Holding Registers (HR)**: Configuration values, setpoints, and writable parameters
2. **Input Registers (IR)**: Sensor readings and status values (read-only)
3. **Coils**: Digital outputs and boolean controls (on/off states)
4. **Discrete Inputs**: Digital inputs and boolean status flags

### Data Interpretations

For each register, the scanner provides multiple interpretations:

```
📍 HR2: 270 (0x010E)
```

- **270**: Raw decimal value
- **0x010E**: Hexadecimal representation
- **Signed interpretation**: Handles negative values (for temperatures below zero)
- **Float interpretation**: Attempts to identify temperature/pressure values

### Common Value Patterns

Based on typical ASHP configurations:

- **Temperature values**: Often in tenths of degrees (270 = 27.0°C)
- **Pressure values**: Usually in tenths of bar (160 = 1.6 bar)
- **Percentage values**: 0-100 or 0-1000 scale
- **Status flags**: 0/1 or specific code values

## 📁 Output Files

The scanner creates JSON files with timestamps:
```
r290_modbus_scan_YYYYMMDD_HHMMSS.json
```

Example structure:
```json
{
  "scan_info": {
    "timestamp": "2024-01-15 14:30:25",
    "host": "192.168.1.100",
    "port": 502,
    "unit_id": 1
  },
  "holding_registers": {
    "2": {
      "value": 270,
      "hex": "0x010E",
      "signed": 270,
      "float_interpretation": "Possible temperature: 27.0°C"
    }
  },
  "input_registers": { ... },
  "coils": { ... },
  "discrete_inputs": { ... }
}
```

## 🔍 Typical Grant R290 Register Ranges

Based on testing, Grant R290 heat pumps typically have:

- **Holding Registers**: 0-100 (configuration and setpoints)
- **Input Registers**: 0-50 (sensor readings)
- **Coils**: 0-50 (digital controls)
- **Discrete Inputs**: 0-20 (status inputs)

Start with these ranges for efficient scanning:
```bash
python3 R290_modbus.py 192.168.1.100 --hr-start 0 --hr-end 100 --ir-start 0 --ir-end 50
```

## 🛠️ Troubleshooting

### Connection Issues

**"No route to host"** or **"Connection refused"**:
- Verify the IP address is correct
- Ensure the heat pump is on the same network
- Check if Modbus TCP is enabled on the heat pump
- Verify the port (usually 502)

**"Connection timeout"**:
- Heat pump may be busy or unresponsive
- Try reducing batch sizes or adding delays
- Check network connectivity

### No Registers Found

- Try different register ranges
- Some heat pumps use non-standard starting addresses
- Verify the unit ID (try 1, 2, or 247)

### Permission Errors

If you get permission errors installing pymodbus:
```bash
# Use virtual environment (recommended)
python3 -m venv modbus_env
source modbus_env/bin/activate
pip install pymodbus

# Or install for user only
pip install --user pymodbus
```

## 📈 Advanced Usage

### Monitoring Specific Registers

Once you've identified interesting registers, monitor them for changes:

```python
# Example: Monitor temperature and pressure registers
python3 R290_modbus.py 192.168.1.100 --monitor
```

### Batch Size Optimization

For slower or busy heat pumps, reduce batch size:
```python
# Modify the script's batch_size parameter in scan methods
# Default is 10, try 5 or 1 for problematic connections
```

### Integration with Home Assistant

Use the discovered registers to create custom Modbus sensors in Home Assistant:

```yaml
# configuration.yaml
modbus:
  - name: grant_r290
    type: tcp
    host: 192.168.1.100
    port: 502
    sensors:
      - name: "Heat Pump Flow Temperature"
        address: 2  # Based on your scan results
        unit_of_measurement: "°C"
        scale: 0.1  # Convert from tenths
        device_class: temperature
```

## 🤝 Contributing

Found issues or improvements? Please contribute:

1. Test with different Grant R290 models
2. Document register meanings and units
3. Report any connection or compatibility issues
4. Share successful configurations

## ⚠️ Important Notes

- **Read-Only Operations**: This scanner only reads data, it doesn't modify settings
- **Network Impact**: Uses minimal bandwidth but adds some network traffic
- **Heat Pump Load**: Designed to be gentle on the heat pump's processing
- **No Warranty**: Use at your own risk, test thoroughly before production use

## 📞 Support

For issues specific to:
- **Grant heat pumps**: Contact Grant UK support
- **Modbus connectivity**: Check your network configuration
- **Home Assistant integration**: Refer to HA Modbus documentation
- **This scanner**: Create an issue in the project repository

---

**Happy scanning!** 🔍 This tool should help you unlock the full potential of your Grant R290 ASHP data for home automation and monitoring.
# Utils Module (`utils.py`)

This module provides utility functions for the Prochidna ESP32 project, mainly for device identification and WiFi connectivity.

---

## Functions

### `generate_default_reader_id()`
- **Purpose:**
  - Generates a unique default reader ID based on the device's MAC address.
- **How it works:**
  - Uses the `network` module to access the device's MAC address.
  - Converts the MAC address to a hexadecimal string.
  - Returns a string in the format: `unidentified_reader/<mac>`.
- **Usage Example:**
  ```python
  reader_id = generate_default_reader_id()
  ```

### `connect_wifi(SSID='prohidna', password='12345678')`
- **Purpose:**
  - Connects the ESP32 to a WiFi network using the provided SSID and password.
- **How it works:**
  - Activates the WiFi interface if not already connected.
  - Attempts to connect to the specified WiFi network.
  - Waits until the connection is established.
  - Returns the network configuration (IP, subnet, gateway, DNS).
- **Usage Example:**
  ```python
  config = connect_wifi('mySSID', 'myPassword')
  print('Connected:', config)
  ```

---

## Integration
- These utilities are used in `main.py` for initial setup and configuration.
- The reader ID is used for MQTT topic naming and device identification.
- WiFi connection is required for all network operations (MQTT, OTA, etc).

---

[Back to Main Documentation](../README.md)

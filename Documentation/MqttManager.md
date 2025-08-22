# MqttManager
# MqttManager Module (`mqtt_manager.py`)

Handles MQTT connection, topic management, message parsing, and publishing for the Prochidna ESP32 Project.

---

## Class: `MqttManager`

### Purpose
- Manages all MQTT-related functionality, including connecting to the broker, subscribing to topics, handling incoming messages (such as whitelist and configuration updates), publishing events (NFC reads, errors, telemetry), and providing callback hooks for integration with other components (LED, whitelist, config, and reset).

### Key Features
- Connects to the MQTT broker using configuration parameters.
- Subscribes to management topics using flexible naming templates.
- Parses and routes incoming messages to appropriate callbacks:
    - Whitelist updates
    - Device reset commands
- Publishes events to MQTT topics, including:
    - NFC read events
    - Online/offline/telemetry status
- Provides an asynchronous message loop for continuous operation.
- Supports clean disconnects and error reporting.

### Usage
- Instantiate with configuration and callback functions:
  ```python
  mqtt = MqttManager(config, led_cb, whitelist_cb, config_cb, reset_cb)
  await mqtt.connect()
  await mqtt.message_loop()
  ```

---

## Integration
- Used in `main.py` to handle all MQTT communication and event publishing.
- Integrates with LED and buzzer modules for feedback on events.
- Configuration and topic templates are set in `config.json`.

---

[Back to Main Documentation](../README.md)
Handles MQTT connection, topic management, message parsing, and publishing for the Prochidna ESP32 Project.

**Purpose:**  
The `MqttManager` class manages all MQTT-related functionality, including connecting to the broker, subscribing to topics, handling incoming messages (such as whitelist and configuration updates), publishing events (NFC reads, errors, telemetry), and providing callback hooks for integration with other components (LED, whitelist, config, and reset).

**Key Features:**
- Connects to the MQTT broker using configuration parameters.
- Subscribes to management topics using flexible naming templates.
- Parses and routes incoming messages to appropriate callbacks:
    - Whitelist updates
    - Configuration changes
    - Device reset commands
- Publishes events to MQTT topics, including:
    - NFC read events
    - Error events
    - Online/offline/telemetry status
- Provides an asynchronous message loop for continuous operation.
- Supports clean disconnects and error reporting.

**Usage:**
- Instantiate with configuration and callback functions:
    - `led_cb`: function to trigger LED animations
    - `whitelist_cb`: function to update the whitelist
    - `config_cb`: function to update configuration variables
    - `reset_cb`: function to reset the device
- Call `connect()` to establish the MQTT connection and subscribe to topics.
- Start the asynchronous `message_loop()` to process incoming messages.
- Use `register_read(data)` and `register_error(error_message)` to publish events.
- Call `disconnect()` for a clean shutdown.

**Configuration Parameters Used:**
- `BROKER_ADDR`: MQTT broker address
- Topic templates: `MQTT_NAMING_TEMPLATE_SUBSCRIBE`, `MQTT_NAMING_TEMPLATE_PUBLISH`
- Event names: `READ_EVENT`, `ERROR_EVENT`, `ONLINE_EVENT`, `OFFLINE_EVENT`, `TELEMETRY_EVENT`
- Management commands: `MANAGE_WHITELIST`, `MANAGE_CONFIG`, `MANAGE_RESET`
- `READER_ID_AFFIX`: unique device identifier for topic naming

**Typical Integration:**
- Created and connected in `main.py` after hardware and WiFi initialization.
- Receives callbacks to update whitelist/config and to trigger device reset.
- Publishes NFC read results and error events as they occur.
- Runs its message loop as a background asynchronous task.
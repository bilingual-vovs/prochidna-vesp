# Main Application Script (`main.py`)

## Overview

The `main.py` file is the central entry point and orchestrator for the Prochidna ESP32 NFC reader system. It handles hardware initialization, configuration management, asynchronous task scheduling, and integrates all major modules (NFC, MQTT, LED, Buzzer, WiFi). The script is designed for robust operation, modularity, and easy adaptation to different board configurations.

---

## Key Responsibilities

- Load and apply configuration from JSON files
- Initialize and manage hardware peripherals (NFC, LED ring, buzzer, SPI)
- Establish WiFi and MQTT connections
- Handle asynchronous tasks for NFC reading, event publishing, and hardware monitoring
- Process incoming MQTT commands for configuration, whitelist, and device management
- Provide callbacks for dynamic configuration and whitelist updates
- Maintain a queue for NFC read events and ensure reliable event publishing

---

## Main Components

### 1. Configuration Management

- Loads configuration from `config.json` (or board-specific variants)
- Applies defaults and generates a unique reader ID if needed
- Supports runtime updates via MQTT (whitelist, config variables)
- Persists changes back to the config file

### 2. Hardware Initialization

- Sets up SPI bus and chip select for the PN532 NFC module
- Initializes the NeoPixel LED ring with color and animation parameters
- Configures the buzzer for audio feedback (approval/denial melodies)
- All hardware objects are globally accessible for task callbacks

### 3. Asynchronous Task Scheduling

- Uses `uasyncio` for lightweight cooperative multitasking
- Core tasks include:
    - NFC tag reading (`read_nfc`)
    - NFC connection monitoring (`check_pn532_connection`)
    - LED animation loop
    - Event publishing queue (`publish_queued_data`)
    - MQTT message loop

### 4. MQTT Integration

- Instantiates `MqttManager` with callbacks for:
    - LED status updates
    - Whitelist management
    - Configuration updates
    - Device reset
- Publishes NFC read and error events using topic templates from config
- Handles incoming MQTT messages for dynamic device management

### 5. NFC Handling

- Connects to and monitors the PN532 NFC module
- Reads NFC tags, checks against the whitelist, and triggers appropriate feedback (LED, buzzer)
- Queues successful reads for MQTT publishing
- Handles connection loss and automatic reconnection

### 6. Event Queue and Publishing

- Maintains a queue of NFC read events
- Publishes events to the MQTT broker using the `MqttManager`
- Ensures no data loss if MQTT or network is temporarily unavailable

### 7. Error Handling and Logging

- Logs all major actions and errors with timestamps
- Reports errors to the MQTT broker for remote diagnostics
- Handles hardware failures gracefully and attempts recovery

---

## Main Functions and Tasks

- `load_config()`, `save_config()`, `apply_config()` — Manage persistent configuration
- `initialize_hardware()` — Sets up all hardware peripherals
- `connect_to_pn532()`, `check_pn532_connection()` — NFC connection management
- `read_nfc()` — Reads NFC tags and processes access logic
- `publish_queued_data()` — Publishes queued events to MQTT
- `handle_whitelist_update()`, `handle_config_update()` — MQTT-driven dynamic updates
- `main()` — Main async entry point; initializes everything and starts all tasks

---

## Example Flow

1. **Startup:** Loads configuration, initializes hardware, connects to WiFi and MQTT broker.
2. **Operation:** Continuously reads NFC tags, checks whitelist, provides feedback, and publishes events.
3. **Remote Management:** Receives MQTT messages to update whitelist/config or trigger reset.
4. **Error Recovery:** Monitors hardware and network, attempts reconnection on failure.

---

## Extending/Customizing

- Add new hardware by extending initialization and task sections
- Integrate new MQTT commands by updating the callback handlers
- Modify LED or buzzer feedback by adjusting config or controller classes

---

## Entry Point

The script is intended to be run directly on the ESP32 as the main application:

```python
if __name__ == "__main__":
        try:
                asyncio.run(main())
        except KeyboardInterrupt:
                # Cleanup and shutdown
```

---

## See Also

- [`buzzer.py`](./buzzer.py) — Buzzer control logic
- [`led.py`](./led.py) — LED ring animations
- [`mqtt_manager.py`](./mqtt_manager.py) — MQTT communication layer
- [`utils.py`](./utils.py) — Utility functions
- [`README.md`](./README.md) — Project overview and configuration guide
# Main Application Script (`main.py`)

## Overview

The `main.py` file is the central entry point and orchestrator for the Prochidna ESP32 NFC reader system. It handles hardware initialization, configuration management, asynchronous task scheduling, and integrates all major modules (NFC, MQTT, LED, Buzzer, WiFi). The script is designed for robust operation, modularity, and easy adaptation to different board configurations.

---

## Key Responsibilities

- Load and apply configuration from JSON files
- Initialize and manage hardware peripherals (NFC, LED ring, buzzer, SPI)
- Establish WiFi and MQTT connections
- Handle asynchronous tasks for NFC reading, event publishing, and hardware monitoring
- Process incoming MQTT commands for configuration, whitelist, and device management
- Provide callbacks for dynamic configuration and whitelist updates
- Maintain a queue for NFC read events and ensure reliable event publishing

---

## Main Components

### 1. Configuration Management

- Loads configuration from `config.json` (or board-specific variants)
- Applies defaults and generates a unique reader ID if needed

### 2. Hardware Initialization
- Sets up SPI, NFC, LED, and buzzer peripherals
- Uses GPIO pins as defined in the configuration

### 3. Network and MQTT
- Connects to WiFi using credentials from config
- Initializes MQTT manager and subscribes to topics

### 4. Event Handling
- Reads NFC tags asynchronously
- Publishes events to MQTT topics
- Handles incoming MQTT messages for configuration and whitelist updates

### 5. Integration
- Coordinates LED and buzzer feedback for user interaction
- Ensures robust operation and error handling

---

## Example Startup Flow
```python
import main
# main.py will initialize all components and start the event loop
```

---

[Back to Main Documentation](../README.md)

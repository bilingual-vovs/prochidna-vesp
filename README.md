# Prochidna ESP32 Project

## Overview

This project implements a smart NFC reader system for ESP32-based hardware, featuring:
- NFC tag reading
- MQTT communication for remote management
- LED ring animations for status indication
- Buzzer for audio feedback
- WiFi connectivity

The codebase is modular and designed for extensibility and easy configuration for different ESP32 boards (e.g., Olimex, Waveshare).

---

## Directory Structure

- `main.py` — Main application entry point, orchestrates all hardware and logic.
- `buzzer.py` — Asynchronous controller for the buzzer (approval/denial sounds).
- `led.py` — Asynchronous controller for NeoPixel LED ring (animations, status).
- `mqtt_manager.py` — Handles MQTT connection, subscriptions, and message routing.
- `utils.py` — Utility functions (WiFi connection, reader ID generation).
- `config.json`, `config_olimex.json`, `config_waveshare.json` — Board-specific configuration files.
- `lib/` — (Optional) Additional libraries, e.g., NFC_PN532 driver.

---

## Module Documentation

### 1. `main.py`
**Purpose:**
Central application logic. Initializes hardware, loads configuration, manages tasks (NFC reading, MQTT, LED, buzzer), and handles callbacks for configuration/whitelist updates.

**Key Features:**
- Loads config from JSON, applies defaults if missing.
- Initializes hardware (SPI, NFC, LED, buzzer).
- Connects to WiFi and MQTT broker.
- Handles incoming MQTT messages (whitelist/config/reset).
- Runs asynchronous tasks for NFC reading, LED animation, MQTT message loop, and data publishing.

**Entry Point:**
Run as main script on the ESP32.

---

### 2. `buzzer.py`
**Purpose:**
Controls a buzzer using PWM for audio feedback (approval/denial melodies).

**Class:**
- `BuzzerController(pin_number, aproval_melody, denial_melody)`
    - `play_approval()` — Plays approval melody asynchronously.
    - `play_denial()` — Plays denial melody asynchronously.
    - `off()` — Turns off the buzzer.

**Usage:**
Instantiate with the GPIO pin and melodies (from config), then call methods as needed.

---

### 3. `led.py`
**Purpose:**
Controls a NeoPixel LED ring for visual feedback (loading, success, failure, waiting animations).

**Class:**
- `LedController(pin_num, num_pixels, ...)`
    - `set_annimation(animation_name, duration)` — Set current animation.
    - `run()` — Main async loop for animation (call with `asyncio.create_task`).
    - `release()` — Stops animation and turns off LEDs.

**Animations:**
- `success`, `failure`, `loading`, `waiting` (breathing effect)

---

### 4. `mqtt_manager.py`
**Purpose:**
Handles MQTT connection, topic management, message parsing, and publishing.

**Class:**
- `MqttManager(config, led_cb, whitelist_cb, config_cb, reset_cb)`
    - `connect()` — Connects to broker, subscribes to topics.
    - `message_loop()` — Async loop for receiving messages.
    - `publish(topic, message)` — Publishes messages.
    - `register_read(data)` — Publishes NFC read event.
    - `register_error(error_message)` — Publishes error event.
    - `disconnect()` — Clean disconnect.

**Topics:**
- Uses templates from config for flexible topic naming.

---

### 5. `utils.py`
**Purpose:**
Utility functions for WiFi connection and reader ID generation.

**Functions:**
- `generate_default_reader_id()` — Returns a unique ID based on MAC address.
- `connect_wifi(SSID, password)` — Connects to WiFi, returns IP config.

---

## Configuration

Configuration is stored in JSON files:
- `config.json` — Default config (Olimex pinout)
- `config_olimex.json` — Olimex board config
- `config_waveshare.json` — Waveshare board config

**Key Parameters:**
- WiFi: `WIFI_SSID`, `WIFI_PASSWORD`
- MQTT: `BROKER_ADDR`, topic templates, reconnect delay
- Hardware: GPIOs for buzzer, SPI, NFC, LED
- Melodies: `APROVAL_MELODY`, `DENIAL_MELODY`
- LED: colors, animation parameters
- Events: topic names for read, error, online, offline, telemetry

**To switch boards:**
Copy the relevant config file to `config.json` or adjust pin numbers as needed.

---

## Usage Guide

1. **Prepare Hardware:**
   - Connect ESP32, NFC module (PN532), NeoPixel ring, and buzzer as per pinout in config.

2. **Configure:**
   - Edit `config.json` for your board and WiFi/MQTT settings.

3. **Deploy Code:**
   - Upload all `.py` files and `config.json` to the ESP32 (e.g., using ampy, rshell, or Pymakr).

4. **Run:**
   - Reset or power-cycle the ESP32. The main script will auto-run.

5. **Monitor:**
   - Use MQTT broker to monitor events, update whitelist/config, or trigger reset.

---

## Extending/Customizing

- **Add new animations:** Extend `LedController`.
- **Change melodies:** Edit config or pass new melodies to `BuzzerController`.
- **Add new MQTT commands:** Update `mqtt_manager.py` and main callbacks.

---

## Troubleshooting

- Check serial output for logs.
- Ensure correct pinout in config for your board.
- Verify WiFi/MQTT credentials.
- Use a compatible MQTT broker (e.g., Mosquitto).

---

## License

MIT License (or specify your own)
# Prochidna ESP32 Project Documentation

Welcome to the Prochidna ESP32 NFC Reader Project! This documentation provides an overview of the system, its modules, configuration, and usage instructions.

---

## Table of Contents
- [Overview](#overview)
- [Modules](#modules)
  - [Main Application](./Documentation/Main.md)
  - [MQTT Manager](./Documentation/MqttManager.md)
  - [LED Controller](./Documentation/LedController.md)
  - [Utils](./Documentation/Utils.md)
  - [Configuration](./Documentation/config.md)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage Example](#usage-example)
- [Board Variants](#board-variants)
- [Extending the Project](#extending-the-project)

---

## Overview

Prochidna is a modular ESP32-based NFC reader system with MQTT integration, LED feedback, and flexible configuration. It is designed for access control, event logging, and IoT applications.

---

## Modules

- **[Main Application](./Documentation/Main.md):** Orchestrates all components, loads configuration, and manages the event loop.
- **[MQTT Manager](./Documentation/MqttManager.md):** Handles MQTT connections, topic management, and event publishing.
- **[LED Controller](./Documentation/LedController.md):** Controls NeoPixel LED ring/strip for visual feedback.
- **[Utils](./Documentation/Utils.md):** Utility functions for device identification and WiFi setup.
- **[Configuration](./Documentation/config.md):** JSON files for all runtime parameters and board-specific settings.

---

## Getting Started

1. **Clone the repository and open in VS Code.**
2. **Configure your board:**
   - Edit `config.json` or use a board-specific file (e.g., `config_waveshare.json`).
3. **Connect your ESP32 hardware.**
4. **Upload the code and configuration files to the device.**
5. **Monitor logs and status via MQTT or serial output.**

---

## Configuration

See [Configuration Documentation](./Documentation/config.md) for all available parameters and their descriptions.

---

## Usage Example

```python
from main import main
main()
```

---

## Board Variants

- `config_waveshare.json` — for Waveshare ESP32 boards
- `config_olimex.json` — for Olimex ESP32 boards
- `config.json` — default configuration

---

## Extending the Project

- Add new modules for additional hardware or features.
- Update configuration files to support new board types.
- Integrate with other IoT systems via MQTT topics.

---

## Links
- [Main Application](./Documentation/Main.md)
- [MQTT Manager](./Documentation/MqttManager.md)
- [LED Controller](./Documentation/LedController.md)
- [Utils](./Documentation/Utils.md)
- [Configuration](./Documentation/config.md)

---

For further details, see the documentation in each module's file.

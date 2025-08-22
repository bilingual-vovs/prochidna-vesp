# Configuration Files (`config.json`, `config_waveshare.json`, `config_olimex.json`)

These JSON files define all runtime parameters for the Prochidna ESP32 project, including network, hardware, and application settings. Board-specific files (e.g., `config_waveshare.json`, `config_olimex.json`) allow for easy adaptation to different ESP32 hardware variants.

---

## Common Parameters

- **CONNECTION_CHECK_INTERVAL**: Interval (seconds) to check connection status.
- **CONNECTION_RETRIES**: Number of retries before reporting connection failure.
- **CLIENT_NAME**: Device name for identification.
- **BROKER_ADDR**: MQTT broker IP address.
- **MQTT_RECONNECT_DELAY**: Delay (seconds) before retrying MQTT connection.
- **NFC_READ_TIMEOUT**: Timeout (seconds) for NFC tag reading.
- **MAX_QUEUE_SIZE**: Maximum number of events in the queue.
- **WHITELIST**: List of allowed NFC tag IDs.
- **MQTT_DELAY**: Delay (ms) between MQTT operations.
- **WIFI_SSID / WIFI_PASSWORD**: WiFi credentials.
- **BUZZER_GPIO**: GPIO pin for buzzer.
- **SPI_SCK_GPIO / SPI_MOSI_GPIO / SPI_MISO_GPIO**: SPI bus pins.
- **NFC_CS_GPIO**: GPIO for NFC chip select.
- **LED_GPIO**: GPIO for LED ring/strip.
- **APROVAL_MELODY / DENIAL_MELODY**: Buzzer melodies for access granted/denied.
- **LED_DIODS_AM**: Number of LEDs in the ring/strip.
- **LED_COLOR_SUCCESS / FAILURE / LOADING / WAITING / OFF**: RGB color values for different states.
- **LED_LOADING_POS / LED_WAITING_PULSE_ANGLE / LED_WAITING_PULSE_SPEED**: Animation parameters.
- **MQTT_NAMING_TEMPLATE_SUBSCRIBE / PUBLISH**: Templates for MQTT topic names.
- **READER_ID_AFFIX**: Suffix for device identification in topics.
- **READ_EVENT / ERROR_EVENT / ONLINE_EVENT / OFFLINE_EVENT / TELEMETRY_EVENT**: Event type names.
- **MANAGE_WHITELIST / CONFIG / RESET**: Management command names.

---

## Usage
- The main application loads the appropriate config file at startup.
- Board-specific files allow for easy switching between hardware variants.
- All hardware and network parameters can be adjusted without code changes.

---

[Back to Main Documentation](../README.md)

# BuzzerController Module (`buzzer.py`)

This module provides an asynchronous controller for a buzzer, supporting approval and denial melodies for user feedback.

---

## Class: `BuzzerController`

### Purpose
- Controls a buzzer connected to a specified GPIO pin on the ESP32.
- Plays approval and denial melodies asynchronously for access feedback.
- Integrates with the main application for audio status indication.

### Constructor
```python
BuzzerController(pin_number, aproval_melody=[[659, 100], [698, 100], [784, 100]], denial_melody=[[523, 200], [440, 200]])
```
- **pin_number**: GPIO pin number for the buzzer.
- **aproval_melody**: List of [frequency, duration_ms] pairs for approval sound.
- **denial_melody**: List of [frequency, duration_ms] pairs for denial sound.

### Methods
- `async play_approval()`: Plays the approval melody asynchronously.
- `async play_denial()`: Plays the denial melody asynchronously.
- `async play_melody(melody)`: Plays a custom melody asynchronously.
- `off()`: Turns off the buzzer immediately.

### Example Usage
```python
buzzer = BuzzerController(pin_number=35)
await buzzer.play_approval()  # Play approval melody
await buzzer.play_denial()    # Play denial melody
buzzer.off()                  # Turn off buzzer
```

---

## Integration
- Used in `main.py` to provide audio feedback for events (NFC read success/failure).
- Melodies are configurable via `config.json`.
- Can be extended for custom sounds or notifications.

---

[Back to Main Documentation](../README.md)

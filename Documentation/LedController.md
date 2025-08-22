# LedController Module (`led.py`)

This module provides an asynchronous controller for a NeoPixel LED ring, supporting various animations and color effects for status indication.

---

## Class: `LedController`

### Purpose
- Controls a NeoPixel LED ring or strip connected to the ESP32.
- Plays different animations and color patterns based on system state (success, failure, loading, waiting, etc).
- Integrates with the main application for visual feedback.

### Constructor
```python
LedController(pin_num, num_pixels, LIGHT_BLUE=(0, 100, 200), PULSE_BLUE=(0, 50, 100), GREEN=(0, 255, 0), RED=(255, 0, 0), BLACK=(0, 0, 0), loading_pos=0, pulse_angle=0.9, pulse_speed=0.1)
```
- **pin_num**: GPIO pin number for the LED data line.
- **num_pixels**: Number of LEDs in the ring/strip.
- **Color and animation parameters**: Customizable for different effects.


### Methods
- `set_annimation(animation_name, duration=0)`: Sets the current animation to play.
- `fill(color)`: Fills all LEDs with the specified color.
- `clear()`: Turns off all LEDs.
- `release()`: Stops the animation task and turns off all LEDs. Should be called to clean up resources when the controller is no longer needed.


### Example Usage
```python
led = LedController(pin_num=34, num_pixels=24)
led.set_annimation('success')
led.fill((0, 255, 0))  # Set all LEDs to green
led.clear()            # Turn off all LEDs
led.release()          # Stop animation and turn off LEDs (cleanup)
```

---

## Integration
- Used in `main.py` to provide visual feedback for events (NFC read, errors, loading, etc).
- Animation and color settings are configurable via `config.json`.

---

[Back to Main Documentation](../README.md)

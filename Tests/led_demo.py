import uasyncio
import time
from led import LedController

# --- Configuration ---
LED_PIN = 32
NUM_PIXELS = 24

# --- Shared State ---
# This dictionary is the "control panel" for the LED animations.
# The default idle state is now 'waiting'.
led_state = 
# Import necessary libraries
import machine
import neopixel
import time

# --- Configuration ---
# According to the Waveshare Wiki, the WS2812 LED is on GPIO 21
PIN_NUM = 21
# There is only one RGB LED on the board
NUM_LEDS = 1
# Control the speed of the color cycle. Smaller number is faster.
# This is the delay in milliseconds between each color step.
CYCLE_SPEED_MS = 15

# --- Initialization ---
# Create a Pin object for the LED
pin = machine.Pin(PIN_NUM, machine.Pin.OUT)

# Create a NeoPixel object to control the LED
np = neopixel.NeoPixel(pin, NUM_LEDS)

def color_wheel(pos):
    """
    Generates a color from the rainbow.
    The input 'pos' is a value from 0 to 255.
    Returns a tuple of (r, g, b) values.
    """
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        # Red to Green
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        # Green to Blue
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        # Blue to Red
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)

print("Starting RGB LED rainbow cycle...")
print("Press Ctrl+C to stop.")

# --- Main Loop ---
# We use a variable 'i' to track our position on the color wheel
i = 0
while True:
    try:
        # Get the color from the wheel function based on position 'i'
        color = color_wheel(i)
        
        # Assign the color to our single LED
        np[0] = color
        
        # Write the color data to the LED
        np.write()
        
        # Wait for a short period
        time.sleep_ms(CYCLE_SPEED_MS)
        
        # Increment our position on the wheel
        i += 1
        
        # If we reach the end of the wheel (255), loop back to the start (0)
        if i > 255:
            i = 0
            
    except KeyboardInterrupt:
        # Clean up and exit if the user presses Ctrl+C
        print("Stopping LED cycle.")
        np[0] = (0, 0, 0) # Turn the LED off
        np.write()
        break
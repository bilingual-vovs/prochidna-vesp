import uasyncio
import time
from led import LedController

# --- Configuration ---
LED_PIN = 32
NUM_PIXELS = 24

# --- Shared State ---
# This dictionary is the "control panel" for the LED animations.
# The default idle state is now 'waiting'.
led_state = {
    'animation': 'waiting', # Initial state
    'duration': 0
}

# A simple logger function
def log(message):
    print(f"[{time.time()}] {message}")

async def main():
    """Main application entry point."""
    log("Starting main application.")

    # 1. Initialize the LED controller
    led_controller = LedController(LED_PIN, NUM_PIXELS, led_state)

    # 2. Start the LED controller's 'run' method as a background task
    log("Creating LED controller task.")
    uasyncio.create_task(led_controller.run())

    # 3. Your main application logic goes here.
    log("Starting main application loop to simulate events.")
    while True:
        # The controller is in 'waiting' state (pulsing blue)
        await uasyncio.sleep(5)
        
        # --- Simulate a process that requires a loader ---
        log("--- Event: Starting a task (e.g., network request) ---")
        led_state['animation'] = 'loading'
        await uasyncio.sleep(4) # Let the loading animation run for 4 seconds
        
        # --- The task finishes successfully ---
        log("--- Event: Task Succeeded ---")
        led_state['animation'] = 'success'
        led_state['duration'] = 2.0 # Show solid green for 2 seconds
        # The controller will automatically return to 'waiting' after this
        
        await uasyncio.sleep(10)
        
        # --- Simulate another task ---
        log("--- Event: Starting another task ---")
        led_state['animation'] = 'loading'
        await uasyncio.sleep(4)
        
        # --- This task fails ---
        log("--- Event: Task Failed ---")
        led_state['animation'] = 'failure'
        led_state['duration'] = 2.0 # Show solid red for 2 seconds
        # The controller will automatically return to 'waiting' after this

# --- Entry Point ---
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
import uasyncio
import time
import neopixel
import math  # We need this for the pulsing (sine wave) effect
from machine import Pin

class LedController:
    """
    An asynchronous controller for a NeoPixel LED ring that plays animations
    based on a shared state dictionary.
    """
    def __init__(self, pin_num, num_pixels,
                # Define standard colors
                LIGHT_BLUE = (0, 100, 200),
                PULSE_BLUE = (0, 50, 100), # Lower intensity for waiting
                GREEN = (0, 255, 0),
                RED = (255, 0, 0),
                BLACK = (0, 0, 0),
                
                # State variables for animations
                loading_pos = 0,
                pulse_angle = 0.9,
                pulse_speed = 0.1       
            ):
        """
        Initializes the controller.
        :param pin_num: The GPIO pin number for the NeoPixel data line.
        :param num_pixels: The number of LEDs in the ring (e.g., 24).
        :param shared_state: A dictionary shared with the main application
                             to control which animation is playing.
                             Expected keys: 'animation' (str), 'duration' (int/float).
        """
        self.np = neopixel.NeoPixel(Pin(pin_num), num_pixels)
        self.num_pixels = num_pixels

        # Define standard colors
        self.LIGHT_BLUE = LIGHT_BLUE
        self.PULSE_BLUE = PULSE_BLUE  # Lower intensity for waiting
        self.GREEN = GREEN
        self.RED = RED
        self.BLACK = BLACK
        
        # State variables for animations
        self.loading_pos = loading_pos
        self.pulse_angle = pulse_angle
        self.pulse_speed = pulse_speed

        self.shared_state = {
            'animation': 'loading', 
            'duration': 0
        }

    def set_annimation(self, animation_name, duration=0):
        self.shared_state['animation'] = animation_name
        self.shared_state['duration'] = duration
        
    def fill(self, color):
        """Helper to fill the entire ring with a single color."""
        self.np.fill(color)
        self.np.write()

    def clear(self):
        """Helper to turn all LEDs off."""
        self.fill(self.BLACK)

    async def _play_solid_color(self, color, duration_s):
        """
        NEW: Lights up the entire ring with a solid color for a set duration.
        """
        self.fill(color)
        await uasyncio.sleep(duration_s)
        self.clear() # Turn off after the duration
            
    def _play_loading_step(self):
        """Advances the loading 'spinner' by one step."""
        self.np.fill(self.BLACK)
        for i in range(4): # 4-pixel long comet tail
            pixel_index = (self.loading_pos - i + self.num_pixels) % self.num_pixels
            intensity_factor = (4 - i) / 4.0
            r, g, b = [int(c * intensity_factor) for c in self.LIGHT_BLUE]
            self.np[pixel_index] = (r, g, b)
        self.np.write()
        self.loading_pos = (self.loading_pos + 1) % self.num_pixels
        
    def _play_pulsing_step(self):
        """
        NEW: Calculates one frame of the slow, pulsing blue animation.
        Uses a sine wave for a smooth breathing effect.
        """
        # Calculate brightness using a sine wave (values from 0.0 to 1.0)
        brightness = (math.sin(self.pulse_angle) + 1) / 4
        
        # Apply brightness to the base pulse color
        r, g, b = [int(c * brightness) for c in self.PULSE_BLUE]
        
        self.fill((r, g, b))
        
        # Increment the angle for the next step. Controls pulse speed.
        self.pulse_angle += self.pulse_speed
        if self.pulse_angle > math.pi * 2:
            self.pulse_angle -= math.pi * 2

    def release(self):
        """
        NEW: Stops the animation task and turns off all LEDs.
        """
        log("Releasing LED controller resources.")
        self.running = False
        self.clear()

    async def run(self):
        """
        The main asynchronous task for the controller.
        This should be started with asyncio.create_task().
        """
        log("LED Controller task started.")
        self.clear()
        self.running = True
        
        while self.running:
            current_animation = self.shared_state.get('animation', 'waiting')

            if current_animation == 'success':
                duration = self.shared_state.get('duration', 1.5)
                await self._play_solid_color(self.GREEN, duration)
                # IMPORTANT: Reset the state back to the default idle animation
                self.shared_state['animation'] = 'waiting'
                
            elif current_animation == 'failure':
                duration = self.shared_state.get('duration', 1.5)
                await self._play_solid_color(self.RED, duration)
                # IMPORTANT: Reset state
                self.shared_state['animation'] = 'waiting'
                
            elif current_animation == 'loading':
                self._play_loading_step()
                await uasyncio.sleep_ms(40) # Controls the speed of the loader
                
            elif current_animation == 'waiting':
                self._play_pulsing_step()
                await uasyncio.sleep_ms(20) # Controls the speed of the pulse
                
            else:
                self.clear()
                await uasyncio.sleep_ms(100)
        log("LED Controller task has stopped.")
        self.clear() # Final cleanup

# A simple logger function
def log(message):
    print(f"[{time.time()}] {message}")
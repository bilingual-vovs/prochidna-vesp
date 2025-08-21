from machine import Pin, PWM
import uasyncio as asyncio

class BuzzerController:
    """Controls a buzzer connected to a specific pin to make approval/denial sounds (asynchronously)."""

    def __init__(self, pin_number,
                 aproval_melody=[
                    [659, 100],  
                    [698, 100],  
                    [784, 100]
                ],
                 denial_melody=[
                    [523, 200],  
                    [440, 200]
                ],):
        self.buzzer_pin = Pin(pin_number, Pin.OUT)  # Set the buzzer pin to output mode.
        self.pwm = PWM(self.buzzer_pin, freq=1000, duty=0)  # Initialize PWM on the buzzer pin (1kHz, initially off).
        self.volume = 512  # Volume of the buzzer (0-1023). Adjust to your needs

        self.aproval_melody = aproval_melody
        self.denial_melody = denial_melody

    async def play_tone(self, frequency, duration_ms, volume):
        """Plays a tone at a specified frequency for a given duration and volume (asynchronously)."""
        self.pwm.freq(frequency)  # Set frequency
        self.pwm.duty(volume)  # Set duty cycle (volume)
        await asyncio.sleep_ms(duration_ms)  # Asynchronous sleep
        self.pwm.duty(0)  # Turn off the buzzer

    async def play_melody(self, melody):
        """Plays the approval melody (asynchronously)."""
        for frequency, duration in melody:
            await self.play_tone(frequency, duration, self.volume)
            await self.play_tone(211, 10, 0) # Pause between tones

    async def play_approval(self):
        for frequency, duration in self.aproval_melody:
            await self.play_tone(frequency, duration, self.volume)
            await self.play_tone(211, 10, 0) # Pause between tones

    async def play_denial(self):
        for frequency, duration in self.denial_melody:
            await self.play_tone(frequency, duration, self.volume)
            await self.play_tone(211, 10, 0) # Pause between tones

    def off(self):
        self.pwm.duty(0)

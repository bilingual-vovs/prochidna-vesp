from machine import Pin, PWM
import uasyncio as asyncio

class BuzzerController:
    """Controls a buzzer connected to a specific pin to make approval/denial sounds (asynchronously)."""

    def __init__(self, pin_number):
        """
        Initializes the BuzzerController.

        Args:
            pin_number (int): The pin number the buzzer is connected to.
        """
        self.buzzer_pin = Pin(pin_number, Pin.OUT)  # Set the buzzer pin to output mode.
        self.pwm = PWM(self.buzzer_pin, freq=1000, duty=0)  # Initialize PWM on the buzzer pin (1kHz, initially off).
        self.approval_freq = 1600  # Frequency for approval sound (Hz)
        self.denial_freq = 600  # Frequency for denial sound (Hz)
        self.duration_ms = 300  # Duration of the sound (milliseconds)
        self.volume = 512  # Volume of the buzzer (0-1023). Adjust to your needs
        self.melody = [(440, 100), (494, 100), (523, 100), (587, 200)] # Add melody

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
            await self.play_tone(211, 50, 0) # Pause between tones

    async def approval_sound(self):
        """Plays the approval sound."""
        await self.play_melody()

    async def denial_sound(self):
        """Plays the denial sound."""
        await self.play_tone(self.denial_freq, self.duration_ms, self.volume)
        await self.play_tone(self.denial_freq, 100, 0) # Pause after tone
        await self.play_tone(self.denial_freq, self.duration_ms, self.volume)

    async def indicate(self, approved):
        """
        Plays the appropriate sound based on the approval status (asynchronously).

        Args:
            approved (bool): True for approval, False for denial.
        """
        if approved:
            await self.approval_sound()
        else:
            await self.denial_sound()


# Example Usage (assuming buzzer is connected to pin 4):
if __name__ == '__main__':

    async def main():
        buzzer = BuzzerController(4)  # Initialize the buzzer controller
        print("Testing buzzer controller...")
        await buzzer.indicate(True)  # Play approval sound
        await asyncio.sleep(1)
        await buzzer.indicate(False)  # Play denial sound
        await asyncio.sleep(1)
        print("Buzzer test complete.")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
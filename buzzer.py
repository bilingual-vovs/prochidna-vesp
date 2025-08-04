from machine import Pin, PWM
import time

class BuzzerController:
    """Controls a buzzer connected to a specific pin to make approval/denial sounds."""

    def __init__(self, pin_number):
        """
        Initializes the BuzzerController.

        Args:
            pin_number (int): The pin number the buzzer is connected to.
        """
        self.buzzer_pin = Pin(pin_number, Pin.OUT) # Set the buzzer pin to output mode.
        self.pwm = PWM(self.buzzer_pin, freq=1000, duty=0) # Initialize PWM on the buzzer pin (1kHz, initially off).
        self.approval_freq = 1600  # Frequency for approval sound (Hz)
        self.denial_freq = 600  # Frequency for denial sound (Hz)
        self.duration_ms = 300  # Duration of the sound (milliseconds)
        self.volume = 800 # Volume of the buzzer (0-1023). Adjust to your needs

    def play_tone(self, frequency, duration_ms, volume):
        """Plays a tone at a specified frequency for a given duration and volume."""
        self.pwm.freq(frequency) # Set frequency
        self.pwm.duty(volume) # Set duty cycle (volume)
        time.sleep_ms(duration_ms)
        self.pwm.duty(0) # Turn off the buzzer

    def approval_sound(self):
        """Plays the approval sound."""
        self.play_melody()

    def play_melody(self):
        """Plays the approval melody (asynchronously)."""
        melody = [
            (440, 100),  # A4
            (494, 100),  # B4
            (523, 100),  # C5
            (587, 200)   # D5 (longer duration)
        ]
        for frequency, duration in melody:
            self.play_tone(frequency, duration, self.volume)
            self.play_tone(211, 50, 0) 

    def denial_sound(self):
        """Plays the denial sound."""
        self.play_tone(self.denial_freq, self.duration_ms, self.volume)
        self.play_tone(self.denial_freq, 100, 0)
        self.play_tone(self.denial_freq, self.duration_ms, self.volume)

    def indicate(self, approved):
        """
        Plays the appropriate sound based on the approval status.

        Args:
            approved (bool): True for approval, False for denial.
        """
        if approved:
            self.approval_sound()
        else:
            self.denial_sound()


# Example Usage (assuming buzzer is connected to pin 4):
if __name__ == '__main__':
    buzzer = BuzzerController(4) # Initialize the buzzer controller
    print("Testing buzzer controller...")
    buzzer.indicate(True) # Play approval sound
    time.sleep(1)
    buzzer.indicate(False) # Play denial sound
    time.sleep(1)
    print("Buzzer test complete.")
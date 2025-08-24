class Light_controller:
    def __init__(self, red, green):
        from machine import Pin, PWM
        self.red_pwm = PWM(Pin(red, Pin.OUT), freq=1000, duty=0)
        self.green_pwm = PWM(Pin(green, Pin.OUT), freq=1000, duty=0)

    def off(self):
        self.red_pwm.duty(0)
        self.green_pwm.duty(0)

    def red_on(self):
        self.off()
        self.red_pwm.duty(1023)
    
    def green_on(self):
        self.off()
        self. green_pwm.duty(1023)

    async def light_green(self, duration):
        import uasyncio as asyncio
        self.green_on()
        await asyncio.sleep(duration)
        self.off()
        
    async def light_red(self, duration):
        import uasyncio as asyncio
        self.red_on()
        await asyncio.sleep(duration)
        self.off()
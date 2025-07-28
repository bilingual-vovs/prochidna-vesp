def blink(times, delay_ms=100):
    import machine
    import time 
    pin = machine.Pin(2, machine.Pin.OUT)

    for _ in range(times):
        pin.value(1) 
        time.sleep_ms(delay_ms)
        pin.value(0) 
        time.sleep_ms(delay_ms)
import machine

print("--- Starting Pin Availability Test ---")
valid_pins = []
invalid_pins = []

for i in range(49):  # ESP32-S3 has pins up to GPIO48
    try:
        pin = machine.Pin(i, machine.Pin.IN)
        # If the above line works, the pin is valid
        valid_pins.append(i)
    except ValueError:
        # If it fails with a ValueError, it's invalid
        invalid_pins.append(i)
    except Exception as e:
        # Catch any other errors
        print(f"Pin {i} caused an unexpected error: {e}")

print("\n--- Results ---")
print("✅ VALID Pins:", sorted(valid_pins))
print("❌ INVALID Pins:", sorted(invalid_pins))
print("\nTest complete. Please share these results.")
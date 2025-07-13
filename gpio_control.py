import time

# Attempt to import RPi.GPIO and handle potential ImportError for development on non-Raspberry Pi environments
try:
    import RPi.GPIO as GPIO
    RASPBERRY_PI_ENVIRONMENT = True
except ImportError:
    print("WARN: RPi.GPIO module not found. Using a mock GPIO interface for development.")
    RASPBERRY_PI_ENVIRONMENT = False
    # Mock GPIO class for development purposes
    class MockGPIO:
        BCM = "BCM_MODE"
        OUT = "OUTPUT_MODE"
        IN = "INPUT_MODE"
        HIGH = 1 # Represents relay ON for active-HIGH relays
        LOW = 0  # Represents relay OFF for active-HIGH relays
        PUD_DOWN = "PULL_DOWN_RESISTOR"
        PUD_UP = "PULL_UP_RESISTOR"

        def __init__(self):
            self._pin_states = {} # Stores the actual pin level (HIGH/LOW)
            self._pin_modes = {}
            self._warnings = True
            self._mode = None
            print("MockGPIO: Initialized (Active-HIGH relay logic assumed for outputs)")

        def setmode(self, mode):
            self._mode = mode
            print(f"MockGPIO: Mode set to {mode}")

        def getmode(self):
            return self._mode

        def setup(self, channel, mode, initial=None, pull_up_down=None):
            self._pin_modes[channel] = {'mode': mode, 'pull_up_down': pull_up_down}
            if mode == self.OUT:
                # For active-HIGH relays, initial=HIGH means ON, initial=LOW means OFF.
                # The 'initial' parameter directly reflects the pin level.
                self._pin_states[channel] = initial if initial is not None else self.LOW # Default to OFF (LOW)
            elif mode == self.IN:
                self._pin_states[channel] = self.LOW if pull_up_down == self.PUD_DOWN else self.HIGH
            print(f"MockGPIO: Pin {channel} setup as {mode}. Initial pin level: {self._pin_states[channel]}. PullUpDown: {pull_up_down}. Relay state: {'ON' if self._pin_states[channel] == self.HIGH else 'OFF' if mode == self.OUT else 'N/A'}")

        def output(self, channel, value): # value is GPIO.LOW or GPIO.HIGH
            if channel not in self._pin_modes or self._pin_modes[channel]['mode'] != self.OUT:
                print(f"MockGPIO: Error - Pin {channel} not setup as OUTPUT.")
                return
            self._pin_states[channel] = value
            relay_state = "ON" if value == self.HIGH else "OFF"
            print(f"MockGPIO: Pin {channel} set to level {value} (Relay {relay_state}).")


        def input(self, channel):
            if channel not in self._pin_modes or self._pin_modes[channel]['mode'] != self.IN:
                print(f"MockGPIO: Error - Pin {channel} not setup as INPUT.")
                return self.LOW # Default to LOW if not setup
            # Simulate sensor behavior for GPIO 24 (Light barrier)
            # For testing, let's assume it goes LOW after some time to simulate card passing
            if channel == 24:
                # This mock doesn't have a dynamic way to change states based on time.
                # We'll assume it's initially HIGH (interrupted) and can be set to LOW by test logic if needed.
                # Or, more simply, just return a toggled state or a fixed state for predictability in tests.
                # For now, returning its last set state, or default if not set.
                current_state = self._pin_states.get(channel, self.HIGH) # Default to HIGH (interrupted)
                print(f"MockGPIO: Pin {channel} read as {current_state}")
                return current_state
            return self._pin_states.get(channel, self.LOW)

        def cleanup(self, channel=None):
            if channel:
                print(f"MockGPIO: Cleanup for pin {channel}")
                if channel in self._pin_states: del self._pin_states[channel]
                if channel in self._pin_modes: del self._pin_modes[channel]
            else:
                print("MockGPIO: General cleanup")
                self._pin_states.clear()
                self._pin_modes.clear()

        def setwarnings(self, value):
            self._warnings = value
            print(f"MockGPIO: Warnings set to {value}")

        # Add dummy methods for features used by some libraries but not directly by this script, if any
        # For example, add_event_detect, remove_event_detect, wait_for_edge etc.
        def add_event_detect(self, *args, **kwargs):
            print(f"MockGPIO: add_event_detect called with args: {args}, kwargs: {kwargs}")

        def remove_event_detect(self, *args, **kwargs):
            print(f"MockGPIO: remove_event_detect called with args: {args}, kwargs: {kwargs}")

        def wait_for_edge(self, *args, **kwargs):
            print(f"MockGPIO: wait_for_edge called with args: {args}, kwargs: {kwargs}")
            # Simulate waiting for an edge; in a real scenario, this would block.
            # For mock, we might simulate a passage of time or an event.
            # Here, we'll just print and return, perhaps after a short mock delay.
            time.sleep(0.1) # Mock delay
            return True # Indicate edge detected for simplicity

    GPIO = MockGPIO() # Use the mock class if RPi.GPIO is not available

# --- GPIO Pin Definitions ---
MOTOR_PIN_1 = 14        # Conveyor motor pin 1
MOTOR_PIN_2 = 16        # Conveyor motor pin 2
SENSOR_PIN = 24         # Light barrier (HIGH = interrupted, LOW = free)
SORT_MOTOR_PIN = 15     # Sorting motor activation
SORT_DIR_LEFT_PIN = 18  # Sorting direction for left side
SORT_DIR_RIGHT_PIN = 19 # Sorting direction for right side

# --- Setup Function ---
def setup_gpio():
    if RASPBERRY_PI_ENVIRONMENT:
        try:
            print("GPIO_CONTROL: Attempting preliminary GPIO cleanup...")
            GPIO.cleanup() # Clean up any existing configurations from previous runs
            print("GPIO_CONTROL: Preliminary GPIO cleanup successful.")
            # GPIO.cleanup() resets the mode, so it needs to be set again.
            GPIO.setmode(GPIO.BCM)
            print("GPIO_CONTROL: GPIO mode set to BCM after preliminary cleanup.")
        except Exception as e:
            print(f"GPIO_CONTROL: Error during preliminary cleanup: {e}. Attempting to proceed...")
            # Ensure mode is set if cleanup failed or wasn't run
            if GPIO.getmode() is None: # Check if mode is already set
                 try:
                    GPIO.setmode(GPIO.BCM)
                    print("GPIO_CONTROL: GPIO mode set to BCM after cleanup error.")
                 except Exception as e_setmode:
                    print(f"GPIO_CONTROL: Critical - Failed to set GPIO mode after cleanup error: {e_setmode}")
                    # Depending on how critical this is, might raise e_setmode or exit
    elif not RASPBERRY_PI_ENVIRONMENT: # Mock environment
        print("GPIO_CONTROL: Using Mock GPIO setup (no preliminary cleanup).")
        GPIO.setmode(GPIO.BCM) # Mock GPIO also needs mode set.

    GPIO.setwarnings(False) # Disable warnings
    # GPIO.setmode(GPIO.BCM) # Mode should be set by now in RPi env, or mock.
    # Ensure mode is set if it wasn't (e.g. RASPBERRY_PI_ENVIRONMENT is False and mock didn't set it, or error path)
    if GPIO.getmode() is None: # Covers cases where RASPBERRY_PI_ENVIRONMENT might be false but GPIO object is real (unlikely but safe)
                               # or if mock GPIO wasn't fully initialized.
        print("GPIO_CONTROL: GPIO mode was None, setting to BCM.")
        GPIO.setmode(GPIO.BCM)


    # Setup output pins - For active-HIGH relays, initial=LOW means relay is OFF.
    GPIO.setup(MOTOR_PIN_1, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(MOTOR_PIN_2, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SORT_MOTOR_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SORT_DIR_LEFT_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SORT_DIR_RIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)

    # Setup input pin for light barrier (logic remains unchanged for sensor)
    # Assuming active HIGH sensor: HIGH when beam is broken, LOW when clear.
    # Use pull-down resistor so it reads LOW when beam is not broken (clear path).
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print(f"GPIO_CONTROL: Pin {MOTOR_PIN_1} (Motor Pin 1) setup as OUT, initial LOW (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {MOTOR_PIN_2} (Motor Pin 2) setup as OUT, initial LOW (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {SORT_MOTOR_PIN} (Sorting Motor) setup as OUT, initial LOW (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {SORT_DIR_LEFT_PIN} (Sorting Dir Left) setup as OUT, initial LOW (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {SORT_DIR_RIGHT_PIN} (Sorting Dir Right) setup as OUT, initial LOW (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {SENSOR_PIN} (Sensor) setup as IN, PULL_DOWN.")
    print("GPIO_CONTROL: GPIO setup complete (Active-HIGH relays).")

# --- Cleanup Function ---
def cleanup_gpio():
    print("GPIO_CONTROL: Cleaning up GPIO pins.")
    if RASPBERRY_PI_ENVIRONMENT or isinstance(GPIO, MockGPIO): # Ensure cleanup is called
        GPIO.cleanup()
    print("GPIO_CONTROL: GPIO cleanup complete.")

# --- Sorting Functions ---
def sort_card_right():
    """
    Sorts the card to the right (successful recognition).
    - GPIO 14 and 16 (MOTOR_PIN_1, MOTOR_PIN_2) einschalten (conveyor motor)
    - Warten, bis GPIO 24 (SENSOR_PIN) HIGH (Karte erkannt)
    - GPIO 15 (SORT_MOTOR_PIN) und 18 (SORT_DIR_RIGHT_PIN) einschalten (sorting motor + direction)
    - Warten, bis GPIO 24 (SENSOR_PIN) LOW (Karte ist durch)
    - Warten, bis GPIO 24 (SENSOR_PIN) wieder HIGH (nächste Karte oder Lücke)
    - GPIO 15 und 18 für 12 ms einschalten (braking)
    - Danach GPIO 15 und 18 ausschalten
    - Nach 600 ms GPIO 14 und 16 ausschalten (conveyor motor)
    """
    print("GPIO_CONTROL: Initiating sort RIGHT sequence.")
    if not RASPBERRY_PI_ENVIRONMENT:
        print("GPIO_CONTROL: MOCK - Simulating sort_card_right() with Active-HIGH relays")

    # GPIO 14 und 16 einschalten (Conveyor Motor ON = HIGH)
    GPIO.output(MOTOR_PIN_1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN_2, GPIO.HIGH)
    print(f"GPIO_CONTROL: Conveyor motors ({MOTOR_PIN_1}, {MOTOR_PIN_2}) ON (Pins HIGH)")

    # Warten, bis GPIO 24 HIGH (Karte erkannt) - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 15 und 18 einschalten (Sorting Motor + Right Direction ON = HIGH)
    GPIO.output(SORT_MOTOR_PIN, GPIO.HIGH)
    GPIO.output(SORT_DIR_RIGHT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Sorting motor ({SORT_MOTOR_PIN}) and right direction ({SORT_DIR_RIGHT_PIN}) ON (Pins HIGH)")

    # Warten, bis GPIO 24 LOW (Karte ist durch) - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card to pass sensor ({SENSOR_PIN} = LOW)...")
    while GPIO.input(SENSOR_PIN) == GPIO.HIGH:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.LOW
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to LOW")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card passed sensor ({SENSOR_PIN} = LOW)")

    # Warten, bis GPIO 24 wieder HIGH (nächste Karte oder Lücke) - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for sensor ({SENSOR_PIN}) to go HIGH again (gap or next card)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH (gap/next card)")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Sensor ({SENSOR_PIN}) is HIGH again.")

    # GPIO 15 und 18 für 12 ms einschalten (braking)
    print(f"GPIO_CONTROL: Activating sorting motor ({SORT_MOTOR_PIN}) and right direction ({SORT_DIR_RIGHT_PIN}) for 12ms braking (Pins HIGH)")
    GPIO.output(SORT_MOTOR_PIN, GPIO.HIGH)
    GPIO.output(SORT_DIR_RIGHT_PIN, GPIO.HIGH)
    time.sleep(0.012) # 12 ms

    # Danach GPIO 15 und 18 ausschalten (Sorting Motor OFF = LOW)
    GPIO.output(SORT_MOTOR_PIN, GPIO.LOW)
    GPIO.output(SORT_DIR_RIGHT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Sorting motor ({SORT_MOTOR_PIN}) and right direction ({SORT_DIR_RIGHT_PIN}) OFF (Pins LOW)")

    # Nach 600 ms GPIO 14 und 16 ausschalten (Conveyor Motor OFF = LOW)
    time.sleep(0.6) # 600 ms
    GPIO.output(MOTOR_PIN_1, GPIO.LOW)
    GPIO.output(MOTOR_PIN_2, GPIO.LOW)
    print(f"GPIO_CONTROL: Conveyor motors ({MOTOR_PIN_1}, {MOTOR_PIN_2}) OFF (Pins LOW)")
    print("GPIO_CONTROL: Sort RIGHT sequence complete.")


def sort_card_left():
    """
    Sorts the card to the left (unsuccessful recognition).
    - GPIO 14 und 16 (MOTOR_PIN_1, MOTOR_PIN_2) einschalten (conveyor motor)
    - Warten, bis GPIO 24 (SENSOR_PIN) HIGH
    - GPIO 15 (SORT_MOTOR_PIN) und 19 (SORT_DIR_LEFT_PIN) einschalten (sorting motor + direction)
    - Warten, bis GPIO 24 (SENSOR_PIN) LOW
    - Warten, bis GPIO 24 (SENSOR_PIN) wieder HIGH
    - GPIO 15 und 19 für 12 ms einschalten (braking)
    - Danach GPIO 15 und 19 ausschalten
    - Nach 600 ms GPIO 14 und 16 ausschalten (conveyor motor)
    """
    print("GPIO_CONTROL: Initiating sort LEFT sequence.")
    if not RASPBERRY_PI_ENVIRONMENT:
        print("GPIO_CONTROL: MOCK - Simulating sort_card_left() with Active-HIGH relays")

    # GPIO 14 und 16 einschalten (Conveyor Motor ON = HIGH)
    GPIO.output(MOTOR_PIN_1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN_2, GPIO.HIGH)
    print(f"GPIO_CONTROL: Conveyor motors ({MOTOR_PIN_1}, {MOTOR_PIN_2}) ON (Pins HIGH)")

    # Warten, bis GPIO 24 HIGH - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 15 und 19 einschalten (Sorting Motor + Left Direction ON = HIGH)
    GPIO.output(SORT_MOTOR_PIN, GPIO.HIGH)
    GPIO.output(SORT_DIR_LEFT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Sorting motor ({SORT_MOTOR_PIN}) and left direction ({SORT_DIR_LEFT_PIN}) ON (Pins HIGH)")

    # Warten, bis GPIO 24 LOW - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card to pass sensor ({SENSOR_PIN} = LOW)...")
    while GPIO.input(SENSOR_PIN) == GPIO.HIGH:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.LOW
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to LOW")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card passed sensor ({SENSOR_PIN} = LOW)")

    # Warten, bis GPIO 24 wieder HIGH - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for sensor ({SENSOR_PIN}) to go HIGH again (gap or next card)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH (gap/next card)")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Sensor ({SENSOR_PIN}) is HIGH again.")

    # GPIO 15 und 19 für 12 ms einschalten (braking)
    print(f"GPIO_CONTROL: Activating sorting motor ({SORT_MOTOR_PIN}) and left direction ({SORT_DIR_LEFT_PIN}) for 12ms braking (Pins HIGH)")
    GPIO.output(SORT_MOTOR_PIN, GPIO.HIGH)
    GPIO.output(SORT_DIR_LEFT_PIN, GPIO.HIGH)
    time.sleep(0.012) # 12 ms

    # Danach GPIO 15 und 19 ausschalten (Sorting Motor OFF = LOW)
    GPIO.output(SORT_MOTOR_PIN, GPIO.LOW)
    GPIO.output(SORT_DIR_LEFT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Sorting motor ({SORT_MOTOR_PIN}) and left direction ({SORT_DIR_LEFT_PIN}) OFF (Pins LOW)")

    # Nach 600 ms GPIO 14 und 16 ausschalten (Conveyor Motor OFF = LOW)
    time.sleep(0.6) # 600 ms
    GPIO.output(MOTOR_PIN_1, GPIO.LOW)
    GPIO.output(MOTOR_PIN_2, GPIO.LOW)
    print(f"GPIO_CONTROL: Conveyor motors ({MOTOR_PIN_1}, {MOTOR_PIN_2}) OFF (Pins LOW)")
    print("GPIO_CONTROL: Sort LEFT sequence complete.")


if __name__ == '__main__':
    # Example usage for testing module directly (if run as script)
    print("GPIO_CONTROL: Running direct test (Active-HIGH relay logic)...")
    try:
        setup_gpio()
        if not RASPBERRY_PI_ENVIRONMENT:
            print("\nMock GPIO Test Simulation (Active-HIGH relays):")
            print(f"Simulating MOTOR_PIN_1 ({MOTOR_PIN_1}) Relay ON (Pin HIGH)")
            GPIO.output(MOTOR_PIN_1, GPIO.HIGH) # Conveyor Motor 1 ON
            time.sleep(0.1)

            print(f"Simulating MOTOR_PIN_2 ({MOTOR_PIN_2}) Relay ON (Pin HIGH)")
            GPIO.output(MOTOR_PIN_2, GPIO.HIGH) # Conveyor Motor 2 ON
            time.sleep(0.1)

            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read (no card): {GPIO.input(SENSOR_PIN)}")
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH # Simulate card detected
            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read (card present): {GPIO.input(SENSOR_PIN)}")

            print(f"Simulating SORT_MOTOR_PIN ({SORT_MOTOR_PIN}) Relay ON (Pin HIGH)")
            GPIO.output(SORT_MOTOR_PIN, GPIO.HIGH) # Sorting Motor ON
            time.sleep(0.1)

            print(f"Simulating SORT_DIR_LEFT_PIN ({SORT_DIR_LEFT_PIN}) Relay ON (Pin HIGH)")
            GPIO.output(SORT_DIR_LEFT_PIN, GPIO.HIGH) # Left Direction ON
            time.sleep(0.1)

            print(f"Simulating SORT_DIR_RIGHT_PIN ({SORT_DIR_RIGHT_PIN}) Relay ON (Pin HIGH)")
            GPIO.output(SORT_DIR_RIGHT_PIN, GPIO.HIGH) # Right Direction ON
            time.sleep(0.1)

            print(f"Simulating MOTOR_PIN_1 ({MOTOR_PIN_1}) Relay OFF (Pin LOW)")
            GPIO.output(MOTOR_PIN_1, GPIO.LOW) # Conveyor Motor 1 OFF
            print(f"Simulating MOTOR_PIN_2 ({MOTOR_PIN_2}) Relay OFF (Pin LOW)")
            GPIO.output(MOTOR_PIN_2, GPIO.LOW) # Conveyor Motor 2 OFF
            print(f"Simulating SORT_MOTOR_PIN ({SORT_MOTOR_PIN}) Relay OFF (Pin LOW)")
            GPIO.output(SORT_MOTOR_PIN, GPIO.LOW) # Sorting Motor OFF
            print(f"Simulating SORT_DIR_LEFT_PIN ({SORT_DIR_LEFT_PIN}) Relay OFF (Pin LOW)")
            GPIO.output(SORT_DIR_LEFT_PIN, GPIO.LOW) # Left Direction OFF
            print(f"Simulating SORT_DIR_RIGHT_PIN ({SORT_DIR_RIGHT_PIN}) Relay OFF (Pin LOW)")
            GPIO.output(SORT_DIR_RIGHT_PIN, GPIO.LOW) # Right Direction OFF

            print("\n--- Simulating sort_card_left (mock) ---")
            sort_card_left()
            print("\n--- Simulating sort_card_right (mock) ---")
            sort_card_right()

        else: # Real RPi environment
            print("Real RPi.GPIO environment. Manual hardware interaction required for full test.")
            print("Basic motor test: Conveyor motors ON (HIGH) for 1s, then OFF (LOW).")
            GPIO.output(MOTOR_PIN_1, GPIO.HIGH)  # Conveyor Motor 1 ON
            GPIO.output(MOTOR_PIN_2, GPIO.HIGH)  # Conveyor Motor 2 ON
            time.sleep(1)
            GPIO.output(MOTOR_PIN_1, GPIO.LOW) # Conveyor Motor 1 OFF
            GPIO.output(MOTOR_PIN_2, GPIO.LOW) # Conveyor Motor 2 OFF
            print("Motor test complete.")

    except Exception as e:
        print(f"GPIO_CONTROL: Error during direct test: {e}")
    finally:
        cleanup_gpio()
    print("GPIO_CONTROL: Direct test finished.")

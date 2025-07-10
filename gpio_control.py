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
        HIGH = 1 # Represents relay OFF for active-LOW relays
        LOW = 0  # Represents relay ON for active-LOW relays
        PUD_DOWN = "PULL_DOWN_RESISTOR"
        PUD_UP = "PULL_UP_RESISTOR"

        def __init__(self):
            self._pin_states = {} # Stores the actual pin level (HIGH/LOW)
            self._pin_modes = {}
            self._warnings = True
            self._mode = None
            print("MockGPIO: Initialized (Active-LOW relay logic assumed for outputs)")

        def setmode(self, mode):
            self._mode = mode
            print(f"MockGPIO: Mode set to {mode}")

        def setup(self, channel, mode, initial=None, pull_up_down=None):
            self._pin_modes[channel] = {'mode': mode, 'pull_up_down': pull_up_down}
            if mode == self.OUT:
                # For active-LOW relays, initial=HIGH means OFF, initial=LOW means ON.
                # The 'initial' parameter directly reflects the pin level.
                self._pin_states[channel] = initial if initial is not None else self.HIGH # Default to OFF (HIGH)
            elif mode == self.IN:
                self._pin_states[channel] = self.LOW if pull_up_down == self.PUD_DOWN else self.HIGH
            print(f"MockGPIO: Pin {channel} setup as {mode}. Initial pin level: {self._pin_states[channel]}. PullUpDown: {pull_up_down}. Relay state: {'OFF' if self._pin_states[channel] == self.HIGH else 'ON' if mode == self.OUT else 'N/A'}")

        def output(self, channel, value): # value is GPIO.LOW or GPIO.HIGH
            if channel not in self._pin_modes or self._pin_modes[channel]['mode'] != self.OUT:
                print(f"MockGPIO: Error - Pin {channel} not setup as OUTPUT.")
                return
            self._pin_states[channel] = value
            relay_state = "ON" if value == self.LOW else "OFF"

            # GPIO 14 and 15 must be the same
            if channel == 14 and self._pin_states.get(15) != value:
                self._pin_states[15] = value
                print(f"MockGPIO: Pin 15 mirrored to level {value} (Relay {relay_state}) due to change in Pin 14.")
            elif channel == 15 and self._pin_states.get(14) != value:
                self._pin_states[14] = value
                print(f"MockGPIO: Pin 14 mirrored to level {value} (Relay {relay_state}) due to change in Pin 15.")
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
MOTOR_PIN = 23         # Conveyor motor
SENSOR_PIN = 24        # Light barrier (HIGH = interrupted, LOW = free)
FLAP_LEFT_A_PIN = 14   # Sorting flap left (part A)
FLAP_LEFT_B_PIN = 15   # Sorting flap left (part B) - must be same state as 14
MAIN_SORT_PIN = 18     # Main sorting mechanism (right, or also for left after delay)

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


    # Setup output pins - For active-LOW relays, initial=HIGH means relay is OFF.
    GPIO.setup(MOTOR_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FLAP_LEFT_A_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FLAP_LEFT_B_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(MAIN_SORT_PIN, GPIO.OUT, initial=GPIO.HIGH)

    # Setup input pin for light barrier (logic remains unchanged for sensor)
    # Assuming active HIGH sensor: HIGH when beam is broken, LOW when clear.
    # Use pull-down resistor so it reads LOW when beam is not broken (clear path).
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print(f"GPIO_CONTROL: Pin {MOTOR_PIN} (Motor) setup as OUT, initial HIGH (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {FLAP_LEFT_A_PIN} (Flap Left A) setup as OUT, initial HIGH (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {FLAP_LEFT_B_PIN} (Flap Left B) setup as OUT, initial HIGH (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {MAIN_SORT_PIN} (Main Sort) setup as OUT, initial HIGH (Relay OFF).")
    print(f"GPIO_CONTROL: Pin {SENSOR_PIN} (Sensor) setup as IN, PULL_DOWN.")
    print("GPIO_CONTROL: GPIO setup complete (Active-LOW relays).")

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
    - GPIO 23 (MOTOR_PIN) einschalten
    - Warten, bis GPIO 24 (SENSOR_PIN) HIGH (Karte erkannt)
    - GPIO 18 (MAIN_SORT_PIN) einschalten
    - Warten, bis GPIO 24 (SENSOR_PIN) LOW (Karte ist durch)
    - Warten, bis GPIO 24 (SENSOR_PIN) wieder HIGH (nächste Karte oder Lücke)
    - GPIO 14 (FLAP_LEFT_A_PIN) und 15 (FLAP_LEFT_B_PIN) gleichzeitig für 25 ms einschalten
    - Danach GPIO 14, 15 und 18 ausschalten
    - Nach 600 ms GPIO 23 ausschalten
    """
    print("GPIO_CONTROL: Initiating sort RIGHT sequence.")
    if not RASPBERRY_PI_ENVIRONMENT:
        print("GPIO_CONTROL: MOCK - Simulating sort_card_right() with Active-LOW relays")

    # GPIO 23 einschalten (Motor ON = LOW)
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) ON (Pin LOW)")

    # Warten, bis GPIO 24 HIGH (Karte erkannt) - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 18 einschalten (Main Sort ON = LOW)
    GPIO.output(MAIN_SORT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) ON (Pin LOW)")

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

    # GPIO 14 und 15 gleichzeitig für 25 ms einschalten (Flaps ON = LOW)
    print(f"GPIO_CONTROL: Activating left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) ON for 25ms (Pins LOW)")
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.LOW)
    time.sleep(0.025) # 25 ms

    # Danach GPIO 14, 15 und 18 ausschalten (Flaps OFF = HIGH, Main Sort OFF = HIGH)
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.HIGH)
    GPIO.output(MAIN_SORT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) OFF (Pins HIGH), Main sort ({MAIN_SORT_PIN}) OFF (Pin HIGH)")

    # Nach 600 ms GPIO 23 ausschalten (Motor OFF = HIGH)
    time.sleep(0.6) # 600 ms
    GPIO.output(MOTOR_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) OFF (Pin HIGH)")
    print("GPIO_CONTROL: Sort RIGHT sequence complete.")


def sort_card_left():
    """
    Sorts the card to the left (unsuccessful recognition).
    - GPIO 23 (MOTOR_PIN) einschalten
    - Warten, bis GPIO 24 (SENSOR_PIN) HIGH
    - GPIO 14 (FLAP_LEFT_A_PIN) und 15 (FLAP_LEFT_B_PIN) gleichzeitig einschalten
    - Nach 10 ms GPIO 18 (MAIN_SORT_PIN) einschalten
    - Warten, bis GPIO 24 (SENSOR_PIN) LOW
    - Warten, bis GPIO 24 (SENSOR_PIN) wieder HIGH
    - GPIO 14 und 15 gleichzeitig ausschalten
    - Nach 25 ms GPIO 18 (MAIN_SORT_PIN) ausschalten
    - Nach 600 ms GPIO 23 (MOTOR_PIN) ausschalten
    """
    print("GPIO_CONTROL: Initiating sort LEFT sequence.")
    if not RASPBERRY_PI_ENVIRONMENT:
        print("GPIO_CONTROL: MOCK - Simulating sort_card_left() with Active-LOW relays")

    # GPIO 23 einschalten (Motor ON = LOW)
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) ON (Pin LOW)")

    # Warten, bis GPIO 24 HIGH - Sensor logic unchanged
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT:
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 14 und 15 gleichzeitig einschalten (Flaps ON = LOW)
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) ON (Pins LOW)")

    # Nach 10 ms GPIO 18 einschalten (Main Sort ON = LOW)
    time.sleep(0.010) # 10 ms
    GPIO.output(MAIN_SORT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) ON (Pin LOW, 10ms after flaps)")

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

    # GPIO 14 und 15 gleichzeitig ausschalten (Flaps OFF = HIGH)
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) OFF (Pins HIGH)")

    # Nach 25 ms GPIO 18 ausschalten (Main Sort OFF = HIGH)
    time.sleep(0.025) # 25 ms
    GPIO.output(MAIN_SORT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) OFF (Pin HIGH, 25ms after flaps off)")

    # Nach 600 ms GPIO 23 ausschalten (Motor OFF = HIGH)
    time.sleep(0.600) # 600 ms
    GPIO.output(MOTOR_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) OFF (Pin HIGH)")
    print("GPIO_CONTROL: Sort LEFT sequence complete.")


if __name__ == '__main__':
    # Example usage for testing module directly (if run as script)
    print("GPIO_CONTROL: Running direct test (Active-LOW relay logic)...")
    try:
        setup_gpio()
        if not RASPBERRY_PI_ENVIRONMENT:
            print("\nMock GPIO Test Simulation (Active-LOW relays):")
            print(f"Simulating MOTOR_PIN ({MOTOR_PIN}) Relay ON (Pin LOW)")
            GPIO.output(MOTOR_PIN, GPIO.LOW) # Motor ON
            time.sleep(0.1)

            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read (no card): {GPIO.input(SENSOR_PIN)}")
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH # Simulate card detected
            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read (card present): {GPIO.input(SENSOR_PIN)}")

            print(f"Simulating FLAP_LEFT_A_PIN ({FLAP_LEFT_A_PIN}) Relay ON (Pin LOW)")
            GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW) # Flaps ON
            time.sleep(0.1)

            print(f"Simulating MAIN_SORT_PIN ({MAIN_SORT_PIN}) Relay ON (Pin LOW)")
            GPIO.output(MAIN_SORT_PIN, GPIO.LOW) # Main sort ON
            time.sleep(0.1)

            print(f"Simulating MOTOR_PIN ({MOTOR_PIN}) Relay OFF (Pin HIGH)")
            GPIO.output(MOTOR_PIN, GPIO.HIGH) # Motor OFF
            print(f"Simulating FLAP_LEFT_A_PIN ({FLAP_LEFT_A_PIN}) Relay OFF (Pin HIGH)")
            GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH) # Flaps OFF
            print(f"Simulating MAIN_SORT_PIN ({MAIN_SORT_PIN}) Relay OFF (Pin HIGH)")
            GPIO.output(MAIN_SORT_PIN, GPIO.HIGH) # Main sort OFF

            print("\n--- Simulating sort_card_left (mock) ---")
            sort_card_left()
            print("\n--- Simulating sort_card_right (mock) ---")
            sort_card_right()

        else: # Real RPi environment
            print("Real RPi.GPIO environment. Manual hardware interaction required for full test.")
            print("Basic motor test: Motor ON (LOW) for 1s, then OFF (HIGH).")
            GPIO.output(MOTOR_PIN, GPIO.LOW)  # Motor ON
            time.sleep(1)
            GPIO.output(MOTOR_PIN, GPIO.HIGH) # Motor OFF
            print("Motor test complete.")

    except Exception as e:
        print(f"GPIO_CONTROL: Error during direct test: {e}")
    finally:
        cleanup_gpio()
    print("GPIO_CONTROL: Direct test finished.")

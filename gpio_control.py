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
        HIGH = 1
        LOW = 0
        PUD_DOWN = "PULL_DOWN_RESISTOR"
        PUD_UP = "PULL_UP_RESISTOR"

        def __init__(self):
            self._pin_states = {}
            self._pin_modes = {}
            self._warnings = True
            self._mode = None
            print("MockGPIO: Initialized")

        def setmode(self, mode):
            self._mode = mode
            print(f"MockGPIO: Mode set to {mode}")

        def setup(self, channel, mode, initial=None, pull_up_down=None):
            self._pin_modes[channel] = {'mode': mode, 'pull_up_down': pull_up_down}
            if mode == self.OUT:
                self._pin_states[channel] = initial if initial is not None else self.LOW
            elif mode == self.IN:
                 # Simulate pull-down by setting initial state to LOW if PUD_DOWN
                self._pin_states[channel] = self.LOW if pull_up_down == self.PUD_DOWN else self.HIGH
            print(f"MockGPIO: Pin {channel} setup as {mode}. Initial: {initial}. PullUpDown: {pull_up_down}. Current State: {self._pin_states.get(channel)}")

        def output(self, channel, value):
            if channel not in self._pin_modes or self._pin_modes[channel]['mode'] != self.OUT:
                print(f"MockGPIO: Error - Pin {channel} not setup as OUTPUT.")
                return
            self._pin_states[channel] = value
            # GPIO 14 and 15 must be the same
            if channel == 14 and self._pin_states.get(15) != value:
                self._pin_states[15] = value
                print(f"MockGPIO: Pin 15 mirrored to {value} due to change in Pin 14.")
            elif channel == 15 and self._pin_states.get(14) != value:
                self._pin_states[14] = value
                print(f"MockGPIO: Pin 14 mirrored to {value} due to change in Pin 15.")
            print(f"MockGPIO: Pin {channel} set to {value}. State: {self._pin_states[channel]}")


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
    if not RASPBERRY_PI_ENVIRONMENT:
        print("GPIO_CONTROL: Using Mock GPIO setup.")

    GPIO.setwarnings(False) # Disable warnings
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering

    # Setup output pins
    GPIO.setup(MOTOR_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(FLAP_LEFT_A_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(FLAP_LEFT_B_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(MAIN_SORT_PIN, GPIO.OUT, initial=GPIO.LOW)

    # Setup input pin for light barrier
    # Assuming active HIGH sensor: HIGH when beam is broken, LOW when clear.
    # Use pull-down resistor so it reads LOW when beam is not broken (clear path).
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print(f"GPIO_CONTROL: Pin {MOTOR_PIN} (Motor) setup as OUT, initial LOW.")
    print(f"GPIO_CONTROL: Pin {FLAP_LEFT_A_PIN} (Flap Left A) setup as OUT, initial LOW.")
    print(f"GPIO_CONTROL: Pin {FLAP_LEFT_B_PIN} (Flap Left B) setup as OUT, initial LOW.")
    print(f"GPIO_CONTROL: Pin {MAIN_SORT_PIN} (Main Sort) setup as OUT, initial LOW.")
    print(f"GPIO_CONTROL: Pin {SENSOR_PIN} (Sensor) setup as IN, PULL_DOWN.")
    print("GPIO_CONTROL: GPIO setup complete.")

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
        print("GPIO_CONTROL: MOCK - Simulating sort_card_right()")

    # GPIO 23 einschalten
    GPIO.output(MOTOR_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) ON")

    # Warten, bis GPIO 24 HIGH (Karte erkannt)
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior for testing
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH # Simulate card arrival
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01) # Poll sensor
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 18 einschalten
    GPIO.output(MAIN_SORT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) ON")

    # Warten, bis GPIO 24 LOW (Karte ist durch)
    print(f"GPIO_CONTROL: Waiting for card to pass sensor ({SENSOR_PIN} = LOW)...")
    while GPIO.input(SENSOR_PIN) == GPIO.HIGH:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior
            GPIO._pin_states[SENSOR_PIN] = GPIO.LOW # Simulate card passing
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to LOW")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card passed sensor ({SENSOR_PIN} = LOW)")

    # Warten, bis GPIO 24 wieder HIGH (nächste Karte oder Lücke)
    # This logic might be tricky: if it's the last card, sensor might stay LOW.
    # Or if cards are very close, it might go HIGH for the next card immediately.
    # For now, implementing as specified. Consider timeout if issues arise.
    print(f"GPIO_CONTROL: Waiting for sensor ({SENSOR_PIN}) to go HIGH again (gap or next card)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior
             # Simulate a brief gap then next card or just clear
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH (gap/next card)")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Sensor ({SENSOR_PIN}) is HIGH again.")

    # GPIO 14 und 15 gleichzeitig für 25 ms einschalten
    print(f"GPIO_CONTROL: Activating left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) ON for 25ms")
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.HIGH)
    time.sleep(0.025) # 25 ms

    # Danach GPIO 14, 15 und 18 ausschalten
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.LOW)
    GPIO.output(MAIN_SORT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) OFF, Main sort ({MAIN_SORT_PIN}) OFF")

    # Nach 600 ms GPIO 23 ausschalten
    time.sleep(0.6) # 600 ms
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) OFF")
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
        print("GPIO_CONTROL: MOCK - Simulating sort_card_left()")

    # GPIO 23 einschalten
    GPIO.output(MOTOR_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) ON")

    # Warten, bis GPIO 24 HIGH
    print(f"GPIO_CONTROL: Waiting for card at sensor ({SENSOR_PIN} = HIGH)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card detected at sensor ({SENSOR_PIN} = HIGH)")

    # GPIO 14 und 15 gleichzeitig einschalten
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) ON")

    # Nach 10 ms GPIO 18 einschalten
    time.sleep(0.010) # 10 ms
    GPIO.output(MAIN_SORT_PIN, GPIO.HIGH)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) ON (10ms after flaps)")

    # Warten, bis GPIO 24 LOW
    print(f"GPIO_CONTROL: Waiting for card to pass sensor ({SENSOR_PIN} = LOW)...")
    while GPIO.input(SENSOR_PIN) == GPIO.HIGH:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior
            GPIO._pin_states[SENSOR_PIN] = GPIO.LOW
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to LOW")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Card passed sensor ({SENSOR_PIN} = LOW)")

    # Warten, bis GPIO 24 wieder HIGH
    print(f"GPIO_CONTROL: Waiting for sensor ({SENSOR_PIN}) to go HIGH again (gap or next card)...")
    while GPIO.input(SENSOR_PIN) == GPIO.LOW:
        if not RASPBERRY_PI_ENVIRONMENT: # Mock sensor behavior
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH
            print(f"MockGPIO: Manually set SENSOR_PIN ({SENSOR_PIN}) to HIGH (gap/next card)")
        time.sleep(0.01)
    print(f"GPIO_CONTROL: Sensor ({SENSOR_PIN}) is HIGH again.")

    # GPIO 14 und 15 gleichzeitig ausschalten
    GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW)
    GPIO.output(FLAP_LEFT_B_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Left flaps ({FLAP_LEFT_A_PIN}, {FLAP_LEFT_B_PIN}) OFF")

    # Nach 25 ms GPIO 18 ausschalten
    time.sleep(0.025) # 25 ms
    GPIO.output(MAIN_SORT_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Main sort mechanism ({MAIN_SORT_PIN}) OFF (25ms after flaps off)")

    # Nach 600 ms GPIO 23 ausschalten
    time.sleep(0.600) # 600 ms
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    print(f"GPIO_CONTROL: Motor ({MOTOR_PIN}) OFF")
    print("GPIO_CONTROL: Sort LEFT sequence complete.")


if __name__ == '__main__':
    # Example usage for testing module directly (if run as script)
    print("GPIO_CONTROL: Running direct test...")
    try:
        setup_gpio()
        # Simulate some activity for mock testing if needed
        if not RASPBERRY_PI_ENVIRONMENT:
            print("\nMock GPIO Test Simulation:")
            print(f"Simulating MOTOR_PIN ({MOTOR_PIN}) ON")
            GPIO.output(MOTOR_PIN, GPIO.HIGH)
            time.sleep(0.1)
            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read: {GPIO.input(SENSOR_PIN)}") # Expected LOW if PUD_DOWN and no interruption

            # Simulate sensor interruption (card present)
            print(f"Simulating sensor interruption (card present) for SENSOR_PIN ({SENSOR_PIN})")
            GPIO._pin_states[SENSOR_PIN] = GPIO.HIGH # Manually set mock sensor state for testing
            print(f"Simulating SENSOR_PIN ({SENSOR_PIN}) read: {GPIO.input(SENSOR_PIN)}") # Expected HIGH

            print(f"Simulating FLAP_LEFT_A_PIN ({FLAP_LEFT_A_PIN}) ON (and B due to rule)")
            GPIO.output(FLAP_LEFT_A_PIN, GPIO.HIGH) # B should follow
            time.sleep(0.1)

            print(f"Simulating MAIN_SORT_PIN ({MAIN_SORT_PIN}) ON")
            GPIO.output(MAIN_SORT_PIN, GPIO.HIGH)
            time.sleep(0.1)

            print(f"Simulating MOTOR_PIN ({MOTOR_PIN}) OFF")
            GPIO.output(MOTOR_PIN, GPIO.LOW)
            print(f"Simulating FLAP_LEFT_A_PIN ({FLAP_LEFT_A_PIN}) OFF (and B)")
            GPIO.output(FLAP_LEFT_A_PIN, GPIO.LOW)
            print(f"Simulating MAIN_SORT_PIN ({MAIN_SORT_PIN}) OFF")
            GPIO.output(MAIN_SORT_PIN, GPIO.LOW)
        else:
            print("Real RPi.GPIO environment. Manual hardware interaction would be needed for full test.")
            # Basic check: turn motor on and off
            GPIO.output(MOTOR_PIN, GPIO.HIGH)
            time.sleep(1)
            GPIO.output(MOTOR_PIN, GPIO.LOW)
            print("Motor test (ON for 1s, then OFF) complete.")

    except Exception as e:
        print(f"GPIO_CONTROL: Error during test: {e}")
    finally:
        cleanup_gpio()
    print("GPIO_CONTROL: Direct test finished.")

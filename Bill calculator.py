import random
from machine import Pin, I2C
import utime
import uos  # MicroPython os module

# Define the I2C bus using SoftI2C
i2c = I2C(scl=Pin(22), sda=Pin(21))

# RTC3231 address
RTC_ADDR = 0x68

# Mount the LittleFS filesystem if not already mounted
try:
    uos.statvfs('/')
except OSError:
    import uerrno
    if uos.mount(uos.LittleFS, '/'):
        print("Filesystem mounted successfully.")
    else:
        print("Failed to mount filesystem.")

# Function to read time from RTC
def read_rtc_time():
    # Send a command byte to set the RTC register pointer to the time
    i2c.writeto(RTC_ADDR, bytes([0x00]))
    
    # Read 7 bytes of data from the RTC
    rtc_data = i2c.readfrom(RTC_ADDR, 7)
    
    # Extract the time components
    second = bcd_to_decimal(rtc_data[0] & 0x7F)  # Seconds (0-59)
    minute = bcd_to_decimal(rtc_data[1] & 0x7F)  # Minutes (0-59)
    hour = bcd_to_decimal(rtc_data[2] & 0x3F)    # Hours (0-23 for 24-hour format)
    return hour, minute, second

# Function to convert BCD to decimal
def bcd_to_decimal(bcd_value):
    return ((bcd_value & 0xF0) >> 4) * 10 + (bcd_value & 0x0F)

# Initialize LED on GPIO Pin 2 for indication
led = Pin(2, Pin.OUT)

# Define current and price constants
CURRENT = 10  # Current in amps
PRICE_PER_UNIT = 35  # Price per unit in currency

# Initialize variables
seconds_counter = 0
price = 0
minute_price_sum = 0
hour_price_sum = 0
minute_counter = 1
hour_counter = 1

# Function to calculate price based on power consumption
def calculate_price(power):
    A_power = power / 1000
    Energy = A_power / 3600
    cost = Energy * PRICE_PER_UNIT
    return cost

# Main loop
while True:
    # Generate a random power consumption value between 180 and 250 watts
    power = random.randint(750, 2500)

    # Read time from RTC
    hour, minute, second = read_rtc_time()

    # Calculate price
    price = calculate_price(power)

    # Print and store data every second
    with open("/data.txt", "a") as data_file:
        led.value(1)
        data_file.write(f"{hour:02d}:{minute:02d}:{second:02d} - Power: {power} watts - Price: {price:.6f}\n")
        led.value(0)

    # Increment seconds counter
    seconds_counter += 1

    # Sum prices every second for minute file
    minute_price_sum += price

    # Create minute file and write sum of prices every 60 seconds
    if seconds_counter % 60 == 0:
        minute_file_name = f"/minute_{minute_counter}.txt"
        with open(minute_file_name, "w") as minute_file:
            minute_file.write(f"Minute {minute_counter} - Price: {minute_price_sum:.6f}\n")
            print(f"Minute {minute_counter} file created with price sum {minute_price_sum}")
        minute_price_sum = 0
        minute_counter += 1

    # Sum prices every 3600 seconds (1 hour) for hour file
    hour_price_sum += price

    # Create hour file and write sum of prices every 3600 seconds
    if seconds_counter % 3600 == 0:
        hour_file_name = f"/hour_{hour_counter}.txt"
        with open(hour_file_name, "w") as hour_file:
            hour_file.write(f"Hour {hour_counter} - Price: {hour_price_sum:.6f}\n")
            print(f"Hour {hour_counter} file created with price sum {hour_price_sum}")
        hour_price_sum = 0
        hour_counter += 1

        # Clear data.txt and remove minute files after each hour
        try:
            with open("/data.txt", "w") as data_file:
                data_file.write("")
                print("Data file cleared.")
        except OSError as e:
            print(f"Error clearing data file: {e}")

        for i in range(1, minute_counter):
            minute_file_path = f"/minute_{i}.txt"
            try:
                uos.remove(minute_file_path)
                print(f"Removed minute file: {minute_file_path}")
            except OSError as e:
                print(f"Error removing minute file: {e}")

    utime.sleep(1)


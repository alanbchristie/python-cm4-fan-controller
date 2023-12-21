#!/usr/bin/env python

"""According to the CM4 IO Board datasheet
(https://datasheets.raspberrypi.com/cm4io/cm4io-datasheet.pdf)
...to enable the I2C bus to the fan controller,
you will need dtparam=i2c_vc=on set in config.txt.
The fan controller will then be on i2c-10 address 0x2f (7-bit address).

My fan is a Waveshare, part number: CM4-FAN-3007-12V and the
practical Fan Speed Range (found empirically) is between between 45 (18%) and 255 (100%).
The fastest speed while remaining quiet is about 70 (27%).
"""
import os
import time
from typing import Tuple

import smbus  # type: ignore

# Hysteresis: 2 degrees?
# So if the trigger for point 4 is 70 degrees
# the fan goes to 100% at 70 degrees or greater
# and remains at 100% until the temperature
# drops to 68 degrees (or less)
HYSTERESIS: int = int(os.environ.get('HYSTERESIS', '2'))

TEMPERATURE_POINT_1: int = int(os.environ.get('TEMPERATURE_POINT_1', '35'))
TEMPERATURE_POINT_2: int = int(os.environ.get('TEMPERATURE_POINT_1', '60'))
TEMPERATURE_POINT_3: int = int(os.environ.get('TEMPERATURE_POINT_1', '65'))
TEMPERATURE_POINT_4: int = int(os.environ.get('TEMPERATURE_POINT_1', '70'))

# A tuple of band speeds (as a percent of full speed).
BAND_SPEED: Tuple[int, int, int, int, int] = (
    int(os.environ.get('BAND_0_SPEED', '0')),
    int(os.environ.get('BAND_1_SPEED', '25')),
    int(os.environ.get('BAND_2_SPEED', '50')),
    int(os.environ.get('BAND_3_SPEED', '75')),
    int(os.environ.get('BAND_4_SPEED', '100')),
)

MEASUREMENT_INTERVAL_S: int = int(os.environ.get('MEASUREMENT_INTERVAL_S', '8'))

# Hardware details of the fan controller
# Bus ID of 10 implies the device /dev/i2c-10 (port I2C10)
BUS_ID: int = 10
FAN_ADDR = 0x2f
FAN_CONTROL_COMMAND = 0x30

# The CPU temperature is written to a sys file.
# It's value is milli-degrees Celsius.
CPU_TEMPERATURE_FILE = '/sys/class/thermal/thermal_zone0/temp'

HIGHEST_BAND: int = len(BAND_SPEED) - 1
CURRENT_BAND: int = 0
CURRENT_TEMPERATURE: float = 0.0

# Create the I2C bus object
SMBUS =  smbus.SMBus(BUS_ID)


def set_fan_speed(temperature_band: int) -> None:
    """Sets the fan speed, given a percentage.
    """
    global CURRENT_BAND
    global BAND_SPEED
    assert temperature_band >= 0 and temperature_band <= HIGHEST_BAND

    if temperature_band == CURRENT_BAND:
        return

    speed_percent: int = BAND_SPEED[temperature_band]
    speed_int = int(speed_percent * 255 / 100)
    print(f'Setting fan speed to {speed_percent}%')
    SMBUS.write_byte_data(FAN_ADDR, FAN_CONTROL_COMMAND, speed_int)
    CURRENT_BAND = temperature_band


def get_cpu_temperature() -> float | None:
    """Read the CPU temperature (from the system file).
    If it fails, or we read nothing we return None. The caller
    should assume the temperature is critical under this condition.
    """
    global CURRENT_TEMPERATURE

    if os.path.isfile(CPU_TEMPERATURE_FILE):
        with open(CPU_TEMPERATURE_FILE, 'r', encoding='utf-8') as ct_file:
            milli_c = ct_file.readline().strip()
        temperature: float = int(milli_c) / 1000.0
        if temperature != CURRENT_TEMPERATURE:
            CURRENT_TEMPERATURE = temperature
            print(f'Temperature is now {temperature}')
        return temperature
    return None


def calculate_temperature_band(temperature: float) -> int:
    """Calculate the new temperature band, given the temperature.
    The new band will depend on the current band,
    the new temperature and hysteresis.
    """
    global CURRENT_BAND

    NEW_BAND: int = CURRENT_BAND
    if CURRENT_BAND == 0:
        # Fan's not running - should it run?
        if temperature >= TEMPERATURE_POINT_1:
            NEW_BAND = 1
        elif temperature >= TEMPERATURE_POINT_2:
            NEW_BAND = 2
        elif temperature >= TEMPERATURE_POINT_3:
            NEW_BAND = 3
        elif temperature >= TEMPERATURE_POINT_4:
            NEW_BAND = 4

    elif CURRENT_BAND == 1:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_2:
            NEW_BAND = 2
        elif temperature >= TEMPERATURE_POINT_3:
            NEW_BAND = 3
        elif temperature >= TEMPERATURE_POINT_4:
            NEW_BAND = 4
        # Do we need to move to a lower band (there is only one below us)?
        if temperature <= TEMPERATURE_POINT_1 - HYSTERESIS:
            NEW_BAND = 0

    elif CURRENT_BAND == 2:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_3:
            NEW_BAND = 3
        elif temperature >= TEMPERATURE_POINT_4:
            NEW_BAND = 4
        # Do we need to move to a lower band?
        if temperature <= TEMPERATURE_POINT_2 - HYSTERESIS:
            NEW_BAND = 1

    elif CURRENT_BAND == 3:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_4:
            NEW_BAND = 4
            return 100
        # Do we need to move to a lower band?
        if temperature <= TEMPERATURE_POINT_3 - HYSTERESIS:
            NEW_BAND = 2

    elif temperature <= TEMPERATURE_POINT_4 - HYSTERESIS:
        NEW_BAND = 3

    assert NEW_BAND >= 0 and NEW_BAND <= HIGHEST_BAND
    if NEW_BAND != CURRENT_BAND:
        msg: str = f'Temperature {temperature} - '
        if NEW_BAND > CURRENT_BAND:
            msg += f'moving up from band {CURRENT_BAND} to {NEW_BAND}'
        else:
            msg += f'moving down from band {CURRENT_BAND} to {NEW_BAND}'
        print(msg)

    return NEW_BAND


# At startup always start the fan for the highest band
set_fan_speed(HIGHEST_BAND)

# Now periodically monitor the temperature
# setting the fan speed using the calculated temperature band.
while True:

    time.sleep(MEASUREMENT_INTERVAL_S)

    current_temperature: float | None = get_cpu_temperature()
    if current_temperature is None:
        print('Temperature read failed - setting fan speed to 100%')
        set_fan_speed(HIGHEST_BAND)
        continue

    temperature_band: int = calculate_temperature_band(current_temperature)
    assert temperature_band >= 0 and temperature_band <= HIGHEST_BAND
    set_fan_speed(temperature_band)

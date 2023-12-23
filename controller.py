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
import logging
import os
import re
import subprocess
import sys
import time
from typing import List

import smbus  # pylint: disable=import-error

# Hysteresis: 2 degrees?
# So if the trigger for point 4 is 70 degrees
# the fan goes to 100% at 70 degrees or greater
# and remains at 100% until the temperature
# drops to 68 degrees (or less)
HYSTERESIS: int = int(os.environ.get("HYSTERESIS", "3"))

LOGGING_LEVEL: str = os.environ.get("LOGGING_LEVEL", "INFO")

MEASUREMENT_INTERVAL_S: int = int(os.environ.get("MEASUREMENT_INTERVAL_S", "8"))

# The 4 temperature point,
# These values define the temperature values for the fan speed bands.
TEMPERATURE_POINT_1: int = int(os.environ.get("TEMPERATURE_POINT_1", "40"))
TEMPERATURE_POINT_2: int = int(os.environ.get("TEMPERATURE_POINT_1", "60"))
TEMPERATURE_POINT_3: int = int(os.environ.get("TEMPERATURE_POINT_1", "65"))
TEMPERATURE_POINT_4: int = int(os.environ.get("TEMPERATURE_POINT_1", "70"))

# A tuple of 5 band speeds (as a percent of full speed).
BAND_SPEED: List[int] = [
    int(os.environ.get("BAND_0_SPEED", "0")),
    int(os.environ.get("BAND_1_SPEED", "25")),
    int(os.environ.get("BAND_2_SPEED", "50")),
    int(os.environ.get("BAND_3_SPEED", "75")),
    int(os.environ.get("BAND_4_SPEED", "100")),
]
HIGHEST_BAND: int = len(BAND_SPEED) - 1

# Hardware details of the fan controller
# Bus ID of 10 implies the device /dev/i2c-10 (port I2C10)
BUS_ID: int = 10
DEGREE_SIGN: str = "\N{DEGREE SIGN}"
FAN_ADDR = 0x2F
FAN_CONTROL_COMMAND = 0x30
MINIMUM_TEMPERATURE_POINT_VALUE: int = 30
MINIMUM_FAN_SPEED_PERCENT: int = 0
MINIMUM_INTERVAL_S: int = 4
MAXIMUM_INTERVAL_S: int = 60

# A record of the current fan speed band
CURRENT_BAND: int = 0

# Create the I2C bus object
SMBUS = smbus.SMBus(BUS_ID)

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.getLevelName(LOGGING_LEVEL),
    format="%(asctime)s.%(msecs)03dZ %(funcName)s():%(lineno)d %(levelname)s # %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger: logging.Logger = logging.getLogger()


def set_fan_speed(band: int) -> None:
    """Sets the fan speed, given a percentage."""
    global CURRENT_BAND  # pylint: disable=global-statement
    assert 0 <= band <= HIGHEST_BAND

    if band == CURRENT_BAND:
        return

    speed_percent: int = BAND_SPEED[band]
    logging.info("Setting fan speed to %s%%", speed_percent)

    speed_int = int(speed_percent * 255 / 100)
    SMBUS.write_byte_data(FAN_ADDR, FAN_CONTROL_COMMAND, speed_int)
    CURRENT_BAND = band


def get_cpu_temperature() -> float | None:
    """Read the CPU temperature, returning the value
    as a rounded integer if it can be found.
    """
    output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    if match := re.search(r"temp=([\d\.]+)'C", output):
        temperature: float = float(match[1])
        logging.debug("%s%sC", temperature, DEGREE_SIGN)
        return temperature
    return None


def calculate_temperature_band(  # pylint: disable=too-many-branches,too-many-statements
    temperature: float,
) -> int:
    """Calculate the new temperature band, given the temperature.
    The new band will depend on the current band,
    the new temperature and hysteresis.
    """
    new_band: int = CURRENT_BAND
    if CURRENT_BAND == 0:
        # Fan's not running - should it run?
        if temperature >= TEMPERATURE_POINT_1:
            new_band = 1
        elif temperature >= TEMPERATURE_POINT_2:
            new_band = 2
        elif temperature >= TEMPERATURE_POINT_3:
            new_band = 3
        elif temperature >= TEMPERATURE_POINT_4:
            new_band = 4

    elif CURRENT_BAND == 1:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_2:
            new_band = 2
        elif temperature >= TEMPERATURE_POINT_3:
            new_band = 3
        elif temperature >= TEMPERATURE_POINT_4:
            new_band = 4
        # Do we need to move to a lower band (there is only one below us)?
        if temperature <= TEMPERATURE_POINT_1 - HYSTERESIS:
            new_band = 0

    elif CURRENT_BAND == 2:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_3:
            new_band = 3
        elif temperature >= TEMPERATURE_POINT_4:
            new_band = 4
        # Do we need to move to a lower band?
        if temperature <= TEMPERATURE_POINT_1 - HYSTERESIS:
            new_band = 0
        elif temperature <= TEMPERATURE_POINT_2 - HYSTERESIS:
            new_band = 1

    elif CURRENT_BAND == 3:
        # Do we need to move up a band?
        if temperature >= TEMPERATURE_POINT_4:
            new_band = 4
            return 100
        # Do we need to move to a lower band?
        if temperature <= TEMPERATURE_POINT_1 - HYSTERESIS:
            new_band = 0
        elif temperature <= TEMPERATURE_POINT_2 - HYSTERESIS:
            new_band = 1
        elif temperature <= TEMPERATURE_POINT_3 - HYSTERESIS:
            new_band = 2

    else:
        # Band 4 - the highest band
        if temperature <= TEMPERATURE_POINT_1 - HYSTERESIS:
            new_band = 0
        elif temperature <= TEMPERATURE_POINT_2 - HYSTERESIS:
            new_band = 1
        elif temperature <= TEMPERATURE_POINT_3 - HYSTERESIS:
            new_band = 2
        elif temperature <= TEMPERATURE_POINT_4 - HYSTERESIS:
            new_band = 3

    assert 0 <= new_band <= HIGHEST_BAND
    if new_band != CURRENT_BAND:
        msg = "Moving up" if new_band > CURRENT_BAND else "Moving down"
        msg += f" from band {CURRENT_BAND} to {new_band}"
        logging.info(msg)

    return new_band


logging.info("Running...")

# Correct temperature points.
# There's a minimum and they must be ordered.
if TEMPERATURE_POINT_1 < MINIMUM_TEMPERATURE_POINT_VALUE:
    logger.warning(
        "TEMPERATURE_POINT_1 too low (%d%s) - setting to %d",
        TEMPERATURE_POINT_1,
        DEGREE_SIGN,
        MINIMUM_TEMPERATURE_POINT_VALUE,
    )
    TEMPERATURE_POINT_1 = MINIMUM_TEMPERATURE_POINT_VALUE
if TEMPERATURE_POINT_2 < TEMPERATURE_POINT_1:
    logger.warning(
        "TEMPERATURE_POINT_2 too low (%d%s) - setting to %d",
        TEMPERATURE_POINT_2,
        DEGREE_SIGN,
        TEMPERATURE_POINT_1,
    )
    TEMPERATURE_POINT_2 = TEMPERATURE_POINT_1
if TEMPERATURE_POINT_3 < TEMPERATURE_POINT_2:
    logger.warning(
        "TEMPERATURE_POINT_3 too low (%d%s) - setting to %d",
        TEMPERATURE_POINT_3,
        DEGREE_SIGN,
        TEMPERATURE_POINT_2,
    )
    TEMPERATURE_POINT_3 = TEMPERATURE_POINT_2
if TEMPERATURE_POINT_4 < TEMPERATURE_POINT_3:
    logger.warning(
        "TEMPERATURE_POINT_4 too low (%d%s) - setting to %d",
        TEMPERATURE_POINT_4,
        DEGREE_SIGN,
        TEMPERATURE_POINT_3,
    )
    TEMPERATURE_POINT_4 = TEMPERATURE_POINT_3

# Correct band speeds.
# There's a minimum and they must be ordered.
if BAND_SPEED[0] < MINIMUM_FAN_SPEED_PERCENT:
    logger.warning(
        "BAND_SPEED[0] too low (%d%%) - setting to %d",
        BAND_SPEED[0],
        MINIMUM_FAN_SPEED_PERCENT,
    )
    BAND_SPEED[0] = MINIMUM_FAN_SPEED_PERCENT
if BAND_SPEED[1] < BAND_SPEED[0]:
    logger.warning(
        "BAND_SPEED[1] too low (%d%%) - setting to %d", BAND_SPEED[1], BAND_SPEED[0]
    )
    BAND_SPEED[1] = BAND_SPEED[0]
if BAND_SPEED[2] < BAND_SPEED[1]:
    logger.warning(
        "BAND_SPEED[2] too low (%d%%) - setting to %d", BAND_SPEED[2], BAND_SPEED[1]
    )
    BAND_SPEED[2] = BAND_SPEED[1]
if BAND_SPEED[3] < BAND_SPEED[2]:
    logger.warning(
        "BAND_SPEED[3] too low (%d%%) - setting to %d", BAND_SPEED[3], BAND_SPEED[2]
    )
    BAND_SPEED[3] = BAND_SPEED[2]
if BAND_SPEED[4] < BAND_SPEED[3]:
    logger.warning(
        "BAND_SPEED[4] too low (%d%%) - setting to %d", BAND_SPEED[4], BAND_SPEED[3]
    )
    BAND_SPEED[4] = BAND_SPEED[3]

# Check hysteresis (must be less than the minimum width of the bands).
SMALLEST_BAND_WIDTH: int = MINIMUM_TEMPERATURE_POINT_VALUE
if TEMPERATURE_POINT_2 - TEMPERATURE_POINT_1 < SMALLEST_BAND_WIDTH:
    SMALLEST_BAND_WIDTH = TEMPERATURE_POINT_2 - TEMPERATURE_POINT_1
elif TEMPERATURE_POINT_3 - TEMPERATURE_POINT_2 < SMALLEST_BAND_WIDTH:
    SMALLEST_BAND_WIDTH = TEMPERATURE_POINT_3 - TEMPERATURE_POINT_2
elif TEMPERATURE_POINT_4 - TEMPERATURE_POINT_3 < SMALLEST_BAND_WIDTH:
    SMALLEST_BAND_WIDTH = TEMPERATURE_POINT_4 - TEMPERATURE_POINT_3
# We must have a minimum bandwidth of 5 degrees if hysteresis is going to make any sense.
if HYSTERESIS > SMALLEST_BAND_WIDTH - 2:
    CHOSEN_HYSTERESIS: int = 2 if SMALLEST_BAND_WIDTH >= 5 else 0
    logger.warning(
        "HYSTERESIS too high (%d%s), and your smallest band is %d%s - setting to %d",
        HYSTERESIS,
        DEGREE_SIGN,
        SMALLEST_BAND_WIDTH,
        DEGREE_SIGN,
        CHOSEN_HYSTERESIS,
    )
    HYSTERESIS = CHOSEN_HYSTERESIS

# Correct measurement interval (there is a minium and a maximum).
if MEASUREMENT_INTERVAL_S < MINIMUM_INTERVAL_S:
    logger.warning(
        "MEASUREMENT_INTERVAL_S too low (%d seconds) - setting to %d",
        MEASUREMENT_INTERVAL_S,
        MINIMUM_INTERVAL_S,
    )
    MEASUREMENT_INTERVAL_S = MINIMUM_INTERVAL_S
elif MEASUREMENT_INTERVAL_S > MAXIMUM_INTERVAL_S:
    logger.warning(
        "MEASUREMENT_INTERVAL_S too high (%d seconds) - setting to %d",
        MEASUREMENT_INTERVAL_S,
        MAXIMUM_INTERVAL_S,
    )
    MEASUREMENT_INTERVAL_S = MAXIMUM_INTERVAL_S

# Check logging level
if LOGGING_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logger.warning("LOGGING_LEVEL not recognised (%s) - setting to INFO", LOGGING_LEVEL)
    LOGGING_LEVEL = "INFO"

# OK - go!
#      ---

logging.info("MEASUREMENT_INTERVAL_S=%d seconds", MEASUREMENT_INTERVAL_S)
logging.info("HYSTERESIS=%d%s", HYSTERESIS, DEGREE_SIGN)
logging.info(
    "TEMPERATURE_POINTS (degrees celsius) %d|%d|%d|%d",
    TEMPERATURE_POINT_1,
    TEMPERATURE_POINT_2,
    TEMPERATURE_POINT_3,
    TEMPERATURE_POINT_4,
)
logging.info(
    "BAND_SPEEDS (percent) %d|%d|%d|%d|%d",
    BAND_SPEED[0],
    BAND_SPEED[1],
    BAND_SPEED[2],
    BAND_SPEED[3],
    BAND_SPEED[4],
)

# At startup always start the fan for the highest band
set_fan_speed(HIGHEST_BAND)

# Now periodically monitor the temperature
# setting the fan speed using the calculated temperature band.
while True:
    time.sleep(MEASUREMENT_INTERVAL_S)

    current_temperature: float | None = get_cpu_temperature()
    if current_temperature is None:
        logging.info(
            "Temperature read failed - setting fan speed to %s%%",
            BAND_SPEED[HIGHEST_BAND],
        )
        set_fan_speed(HIGHEST_BAND)
        continue

    temperature_band: int = calculate_temperature_band(current_temperature)
    assert 0 <= temperature_band <= HIGHEST_BAND
    set_fan_speed(temperature_band)

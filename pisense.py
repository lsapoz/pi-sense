import json
import pathlib
import time
import threading

import serial
import board
import busio
import adafruit_bme280
import adafruit_pm25
import adafruit_sgp30

from influxdb import InfluxDBClient

def monitor_pm25(pm25_sensor: adafruit_pm25.PM25, influx_client: InfluxDBClient):
    # store the previous data point to compare with next reading
    # the sensor outputs data faster than its own sample rate
    # to avoid the duplicate readings, we'll avoid logging data that hasn't changed
    # it's pretty unlikely that no readings change when the sensor actually re-samples the air
    previous_data = {}
    
    while True:
        # throttle
        time.sleep(.5)

        try:
            aqdata = pm25_sensor.read()
        except RuntimeError:
            # Unable to read from PM2.5 sensor, try again on the next iteration
            continue

        if aqdata == previous_data:
            # no new data, try again on the next iteration
            continue

        previous_data = aqdata.copy()

        print(f"PM env - 1.0:{aqdata['pm10 env']} 2.5:{aqdata['pm25 env']} 10:{aqdata['pm100 env']}")

        json_data = [
            {
                "measurement": "environmental_pm",
                "fields": {
                    "pm10": aqdata["pm10 env"],
                    "pm25": aqdata["pm25 env"],
                    "pm100": aqdata["pm100 env"]
                }
            }
        ]
        influx_client.write_points(json_data)


def monitor_bme280(bme_280: adafruit_bme280.Adafruit_BME280, influx_client: InfluxDBClient):
    readings = {}

    while True:
        # throttle
        time.sleep(10)

        readings['temperature'] = bme280.temperature
        readings['humdity'] = bme280.humidity
        readings['pressure'] = bme280.pressure

        print(f"BME280 - Temp:{readings['temperature']:.2f}°C Hum:{readings['humdity']:.2f}% P:{readings['pressure']:.2f}hPa")

        json_data = []
        for measurement, value in readings.items():
            json_data.append(
                {
                    "measurement": measurement,
                    "fields": {
                        "value": value
                    }
                }   
            )
        influx_client.write_points(json_data)


def monitor_sgp30(sgp30: adafruit_sgp30.Adafruit_SGP30, influx_client: InfluxDBClient):
    # get the serial number of the connected SGP30 and store it as a string
    serial_str = str(sgp30.serial)

    # read in the baseline values previously saved for this sensor
    config_file_path = pathlib.Path(__file__).parent / 'sgp30.json'
    baseline = {}
    try:
        with open(config_file_path) as f:
            config_data = json.load(f)
            if serial_str in config_data:
                baseline = config_data.get(serial_str)
    except FileNotFoundError:
        print('SGP30 - No stored configuration found')
    except ValueError:
        print('SGP30 - Stored configuration is invalid')

    # if no stored baseline is available, sensor must first run for 12 hours before data is accurate enough to log
    ok_to_log = False
    first_log_time = time.time() + (12 * 60 * 60)

    # during normal operation, we'll want to log the baseline every hour
    next_baseline_read = time.time() + (60 * 60)

    if baseline:
        try:
            print(f"SGP30 - Initalizing baseline -  eCO2:{baseline['baseline_eCO2']} TVOC:{baseline['baseline_TVOC']}")
            sgp30.set_iaq_baseline(baseline['baseline_eCO2'], baseline['baseline_TVOC'])

            # since we set the baseline, we can start logging data after a short 1 minute warm-up
            first_log_time = time.time() + 60
        except RuntimeError:
            print("SGP30 - Attempted to write an invalid baseline")
    
    readings = {}

    while True:
        # throttle
        time.sleep(1)

        readings['eCO2'] = sgp30.eCO2
        readings['TVOC'] = sgp30.TVOC

        print(f"SGP30 - eCO2:{readings['eCO2']} ppm TVOC:{readings['TVOC']} ppb")

        if not ok_to_log:
            if time.time() < first_log_time:
                continue
            ok_to_log = True
            print("SGP30 - Adjustment complete, beginning to log data")

        # if it's been an hour since our last baseline read, log it to file now
        if time.time() > next_baseline_read:
            baseline['baseline_eCO2'] = sgp30.baseline_eCO2
            baseline['baseline_TVOC'] = sgp30.baseline_TVOC
            config_data = {
                serial_str: baseline
            }
            with open(config_file_path, 'w') as f:
                json.dump(config_data, f)
            next_baseline_read = time.time() + (60 * 60)

        json_data = []
        for measurement, value in readings.items():
            json_data.append(
                {
                    "measurement": measurement,
                    "fields": {
                        "value": value
                    }
                }   
            )
        influx_client.write_points(json_data)


# Create a client to write data to InfluxDB
influx_client = InfluxDBClient(database='pisense')

# create database if it does not already exist
influx_client.create_database('pisense')

# Connect to a PM2.5 sensor over UART
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
pm25_sensor = adafruit_pm25.PM25_UART(uart)
print("Found PM2.5 sensor")

# Connect to BME280 over I2C
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
print("Found BME280")

# Connect to SGP30 over I2c
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
print("Found SGP30")

# set up a daemon thread to poll each sensor
polls = []
polls.append(threading.Thread(target=monitor_pm25, args=(pm25_sensor, influx_client), daemon=True))
polls.append(threading.Thread(target=monitor_bme280, args=(bme280, influx_client), daemon=True))
polls.append(threading.Thread(target=monitor_sgp30, args=(sgp30, influx_client), daemon=True))

# start each polling thread and call join to run forever
for t in polls:
    t.start()
for t in polls:
    t.join()

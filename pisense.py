import time
import threading

import serial
import board
import busio
import adafruit_bme280
import adafruit_pm25

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
        except RuntimeError as err:
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

        print(f"BME280 - Temp:{readings['temperature']}°C Hum:{readings['humdity']}% P:{readings['pressure']}hPa")

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

# set up a daemon thread to poll each sensor
polls = []
polls.append(threading.Thread(target=monitor_pm25, args=(pm25_sensor, influx_client), daemon=True))
polls.append(threading.Thread(target=monitor_bme280, args=(bme280, influx_client), daemon=True))

# start each polling thread and call join to run forever
for t in polls:
    t.start()
for t in polls:
    t.join()

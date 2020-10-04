import time
import serial
from influxdb import InfluxDBClient

from pm25 import plantower_pm25

# Create a client to write data to InfluxDB
influx_client = InfluxDBClient(database='pisense')

# create database if it does not already exist
influx_client.create_database('pisense')

# Connect to a PM2.5 sensor over UART
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
pm25_sensor = plantower_pm25.PM25_UART(uart)
print("Found PM2.5 sensor, reading data...")

# store the previous data point to compare with next reading
# the sensor outputs data faster than its own sample rate
# to avoid the duplicate readings, we'll avoid logging data that hasn't changed
# it's pretty unlikely that no readings change when the sensor actually re-samples the air
previous_data = {}

while True:
    time.sleep(.5)

    try:
        aqdata = pm25_sensor.read()
    except RuntimeError as err:
        print(f"Unable to read from sensor ({err}), retrying...")
        continue

    if aqdata == previous_data:
        print("Data did not change, skipping...")
        continue

    previous_data = aqdata.copy()

    print()
    print("Concentration Units (standard)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
    )
    print("Concentration Units (environmental)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
    )
    print("---------------------------------------")
    print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
    print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
    print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
    print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
    print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
    print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
    print("---------------------------------------")

    json_data = [
        {
            "measurement": "environmental_pm",
            "tags" : {
                "location": "indoors"
            },
            "fields": {
                "pm10": aqdata["pm10 env"],
                "pm25": aqdata["pm25 env"],
                "pm100": aqdata["pm100 env"]
            }
        }
    ]
    influx_client.write_points(json_data)

# Pi-sense
Home environmental monitor running on a Raspberry Pi. After the [2020 wildfires](https://en.wikipedia.org/wiki/2020_Western_United_States_wildfire_season) blanketed Seattle in smoke, I wanted a way to monitor the air quality indoors. And while we're at it, might as well add on a few other sensors just for fun.

## Sensors
- [PMS5003 Particulate Matter Sensor](https://learn.adafruit.com/pm25-air-quality-sensor)
- [BME280 Temperature/Humidity/Pressure Sensor](https://learn.adafruit.com/adafruit-bme280-humidity-barometric-pressure-temperature-sensor-breakout)
- [SGP30 TVOC/eCO2 Gas Sensor](https://learn.adafruit.com/adafruit-sgp30-gas-tvoc-eco2-mox-sensor)

## Raspberry Pi Setup
1. Set up the SD card for the Raspberry Pi
    1. [Download Raspbian Lite](https://www.raspberrypi.org/downloads/raspberry-pi-os/)
    1. [Add a wpa_supplicant file](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md) to the boot folder and configure it to have the Pi automatically connect via Wi-Fi
    1. Add an empty `ssh` file to the boot folder to enable SSH access
    1. Flash the image onto the SD card using a tool like [balenaEtcher](https://www.balena.io/etcher/)
1. Plug the Pi in, wait for it to boot, and connect via ssh `ssh pi@raspberrypi.local` (default password is `raspberry`)
1. Update all the currently installed packages `sudo apt update && sudo apt upgrade`
1. Use `sudo raspi-config` to: 
    1. [Disable the serial console](https://www.raspberrypi.org/documentation/configuration/uart.md) and reclaim the primary UART for our usage
    1. Enable I2C
    1. Change the hostname. On subsequent boots, you should be able reach the Pi at `HOSTNAME.local` on your network (e.g. `ssh pisense.local`)
    1. Change the `pi` user's password to something that isn't the default
1. [Install Grafana](https://grafana.com/grafana/download?platform=arm) and verify you can access it via your web browser
    1. Use the ARMv7 package for a Raspberry Pi 3 and the ARMv6 package for a Raspberry Pi Zero
    1. Configure Grafana to run on startup `sudo systemctl enable grafana-server`
1. [Install InfluxDB](https://docs.influxdata.com/influxdb/v1.8/introduction/install/) using the Debian instructions

## Running the script
1. Clone the repo and `cd` into the project
1. Set up a virtual environment `python3 -m venv .env`
1. Activate the virtual environment `source .env/bin/activate`
1. Install the dependencies `pip3 install -r requirements.txt`
1. Run the script `python3 pisense.py`

## Starting automatically on boot
Once the steps to run the script are complete, the system can be configured to automatically run on boot.
1. Copy the systemd unit file to the correct directory `sudo cp pisense.service /etc/systemd/system`
1. Start the service `sudo systemctl start pisense`
1. Ensure it's running correctly by checking its status (`sudo systemctl status pisense`) and monitoring its output (`sudo journalctl -f -u pisense`)
1. If everything looks good, set it up to start on boot `sudo systemctl enable pisense`

NOTE: The `pisense.service` file assumes the project is cloned to `/home/pi`, the location should be updated if its cloned elsewhere

NOTE 2: If you need to run the script manually again after the service has been enabled, stop the systemd service first `sudo systemctl stop pisense`

## Setting up Grafana Dashboard
1. Configure the local instance of InfluxDB as a data source using `pisense` as the database
1. Import the [dashboard file](/grafana) and connect it to the data source

## Configuration files

### SGP30
The SGP30 needs to run for 12 hours before a reasonable baseline can be stored. The script will run the sensor for 12 hours before it saves the baseline values to an `sgp30.json` file at the project root. Once the baseline values are stored, the script will begin to save sensor readings. The baseline values on disk are then updated once an hour. 

On subsequent startups, the baseline will be read from file and applied to the sensor so the 12 hour warm-up period can be skipped. The baseline values are associated with the serial number of the sensor to prevent values from one sensor being applied to a different sensor. 

More details on this behavior can be found [here](https://forums.adafruit.com/viewtopic.php?f=19&p=677642#p661509).

### BME280
The BME280 temperature reading is susceptible to self-heating. If it's near other components that generate heat (e.g. a Raspberry Pi), the ambient temperature can be thrown off even more. And since the relative humidity is temperature-dependent, it throws that off as well. 

Testing shows that the offset is fairly constant, so we can compensate for it after reading the temperature and humidity. We can determine the offset by comparing raw readings to a trusted thermometer placed near the sensor. 

To apply temperature compensation, add a `bme280.json` file to the project root. The contents should be:
```
{
    "temp_offset": -2.8
}
```
The value of `"temp_offset"` should be the °C you want to offset the temperature reading by.

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
1. Plug the Pi in, wait for it to boot, and connect via ssh
1. Update all the currently installed packages `sudo apt update && sudo apt upgrade`
1. Use `sudo raspi-config` to 
    1. [Disable the serial console](https://www.raspberrypi.org/documentation/configuration/uart.md) and reclaim the primary UART for our usage
    1. Enable I2C
    1. Always a good idea to change the `pi` user's password while you're in here
1. [Install Grafana](https://grafana.com/tutorials/install-grafana-on-raspberry-pi/#3) and verify you can access it via your web browser
1. [Install InfluxDB](https://docs.influxdata.com/influxdb/v1.8/introduction/install/) using the Debian instructions

## Running the script
1. Clone the repo and `cd` into the project
1. Set up a virtual environment `python3 -m venv .env`
1. Activate the virtual environment `source .env/bin/activate`
1. Install the dependencies `pip3 install -r requirements.txt`
1. Run the script `python3 pisense.py`

## Starting automatically on boot
Once the steps to run the script are complete, the system can be configued to automatically run on boot.
1. Copy the systemd unit file to the correct directory `sudo cp pisense.service /etc/systemd/system`
1. Start the service `sudo systemctl start pisense`
1. Ensure it's running correctly by checking its status (`sudo systemctl status pisense`) and monitoring its output (`sudo journalctl -f -u pisense`)
1. If everything looks good, set it up to start on boot `sudo systemctl enable pisense`

NOTE: The `pisense.service` file assumes the project is cloned to `/home/pi`, the location should be updated if its cloned elsewhere

NOTE 2: If you need to run the script manually again after the service has been enabled, stop the systemd service first `sudo systemctl stop pisense`

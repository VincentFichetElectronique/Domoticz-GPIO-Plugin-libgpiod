# Domoticz-GPIO-Plugin

Controls GPIO pins on a Raspberry Pi.

## Key Features

* Creates one Domoticz device per relay.
* Support trixie debian.

## Installation

Python version 3.13.5 or higher required & Domoticz version 2026.4 or greater.

To install:
* Run ```sudo apt-get install python3-libgpiod```
* Go in your Domoticz directory, open the plugins directory.
* Navigate to the directory using a command line
* Run: ```git clone https://github.com/VincentFichetElectronique/Domoticz-GPIO-Plugin-libgpiod```
* Restart Domoticz.

In the web UI, navigate to the Hardware page.  In the hardware dropdown there will be an entry called "Raspberry Pi GPIO".

## Updating

To update:
* Go in your Domoticz directory using a command line and open the plugins directory then the Domoticz-GPIO-Plugin directory.
* Run: ```git pull```
* Restart Domoticz.

## Configuration

| Field | Information|
| ----- | ---------- |
| Output GPIO Pins | Comma delimited list of output (relay) GPIO pins. Format is pin number colon NC or NO or TO colon 0 or 1  ( e.g 16:TO:1, for GPIO16 where TO is for "On/Off" Button, NO is "Push On" Button, NC is a "Push Off" Button. 1 means active_low switch, 0 means active_high switch ) |
| Input GPIO Pins | Comma delimited list of board GPIO pin (e.g 2 for GPIO2, 14 for PGIO14, ...) to check for input |
| Heartbeat Frequency | Determines how often Input Pins are checked for values in seconds |
| Debug | When true the logging level will be much higher to aid with troubleshooting |

## Change log

| Version | Information|
| ----- | ---------- |
| 2.0.0 | Initial upload version |

# Site Monitor

===========

## Overview

Python app that runs under systemd and pings a set of urls every two miutes. The results
are publish on a home Mqtt topic to be consumed by other devices.


### Requirements

```
sudo pip3 install octopus-http
sudo pip3 install paho-mqtt

```

### Usage

```
python3 monitor.py
```

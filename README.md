# Jenkins warning light using a USB HID relay

Python script to monitor a Jenkins job overview to switch a relay controlling a warning light if builds are failing.

## Demo

[![Demo of the extreme feedback Jenkins flashing light](http://img.youtube.com/vi/jDgX5bndHAk/0.jpg)](http://www.youtube.com/watch?v=jDgX5bndHAk "Demo of the extreme feedback Jenkins flashing light")

## Requirements

* Windows
* Python 3
* Cheap chinese USB relay, like these:
![Image of USB Relay](relay.jpg?raw=true)

## Usage

`python jenkins-warnings-light.py [url to a Jenkins view]`

example:

`hid-relay>python jenkins-warnings-light.py https://ci.adoptopenjdk.net/job/build-scripts/job/jobs/job/jdk11u/`

## License

The DLL comes from https://github.com/pavel-a/usb-relay-hid, which reuses some code from other V-USB projects, which is dual-licensed: GPL + commercial.

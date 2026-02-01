# Firmware Flasher 9000

- Flashing utlity for STM32 boards utilizing SocketCAN or CANlib

# General setup

- Set up a python environment inside SocketCAN or CANlib
  ```
  python -m venv venv
  ```
- Activate the environment
  ```
  source /venv/bin/activate
  ```

# SocketCAN

## Installation

- pip install python-can
- To run a script:

```
./run.sh [script.py]
```

- **Note:** There is a [setup.sh] script provided

# CANlib

## Installation

- Download CANlib through Kvaser's website:
  - https://kvaser.com/single-download/?download_id=47112

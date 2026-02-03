# Firmware Flasher 9000

- Flashing utlity for STM32 boards utilizing SocketCAN or CANlib

# Requirements

- [Python](https://www.python.org/downloads/)

# General Setup

- Set up a python environment inside SocketCAN or CANlib directory and activate it

```bash
  python -m venv venv
  source venv/bin/activate
```

- Install the necessary libraries using pip

```bash
  pip install -r requirements.txt
```

# SocketCAN

## Usage

- There is a provided bash script SocketCAN

```bash
./run.sh [script.py]
```

- There is also a provided [setup.sh] script

# CANlib

## Additional Setup

- Download CANlib and Kvaser Drivers through Kvaser's website:
  - [Kvaser Drivers for Windows](https://kvaser.com/single-download/?download_id=47112)
  - [Kvaser CANlib SDK](https://kvaser.com/single-download/?download_id=47105)
- Optional:
  - [Kvaser CanKing](https://kvaser.com/single-download/?download_id=486884)

# Explanation of the files

```bash
'detect_channels_[...].py': Used for detecting channels, testing the setup
'receive_[...].py': Used to test receiving functionality on the Bootloader side
'flashing_[...].py': Used to flash the Application using the Bootloader
```

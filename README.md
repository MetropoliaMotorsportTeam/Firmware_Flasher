<h1 align="center">Firmware Flasher</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-2b6cb0?style=flat-square" alt="version">
  <img src="https://img.shields.io/badge/python-3.11%2B-4a5568?style=flat-square" alt="python">
</p>

<p align="center">CAN-based firmware flashing tool for STM32 boards, over SocketCAN or CANlib.</p>

## Install

```bash
python -m venv venv
source venv/bin/activate

# Linux, SocketCAN
pip install -e .[socketcan]

# Windows, CANlib (Kvaser hardware/drivers required)
pip install -e .[canlib]
```

## Usage

```bash
flash --backend socketcan --port can0 --baud 1000000 firmware.bin
flash --backend canlib --port 0 --baud 1000000 firmware.bin
flash --config flash.toml firmware.bin
```

`--backend` is always required. CLI flags override values from
`--config` when both are given.

## Configuration file

Copy `flash.toml.example` to `flash.toml` and adjust:

```toml
backend = "socketcan"
port = "can0"
baud = 1000000
retries = 5
timeout_ms = 5000
```

## Development

```bash
pip install -e .[socketcan,test]
pytest -v --cov=flasher --cov-report=term-missing
```

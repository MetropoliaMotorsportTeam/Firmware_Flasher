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

Flashing prints each stage, the CRC and chunk count, and a progress line
per chunk. Add `--verbose` to also print every CAN frame sent and received.

## Configuration file

Copy `flash.toml.example` to `flash.toml` and adjust:

```toml
backend = "socketcan"
port = "can0"
baud = 1000000
retries = 5
timeout_ms = 5000
```

## Bringing up a SocketCAN interface

Linux only. Run once per boot, replacing `can0` and the bitrate as needed:

```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

## Diagnostics

`can-diag` is a read-only helper for checking the bus. It does not flash anything.

```bash
can-diag channels --backend socketcan            # list CAN interfaces and their state
can-diag channels --backend socketcan --verbose  # also show the full ip link output
can-diag channels --backend canlib               # list Kvaser channels
can-diag listen --backend socketcan --port can0 --baud 1000000             # print every frame until Ctrl-C
can-diag probe --backend socketcan --port can0 --baud 1000000 --duration 5 # trigger the jump and wait for the app's ACK
```

`probe` waits for the application's alive ACK. Its ID defaults to the value
for the chosen backend; override it with `--app-id` (for example `--app-id 0x7D0`).

## Troubleshooting probe failures

If `can-diag probe` reports no alive ACK, check these in order:

1. The bootloader's jump to the application failed.
2. The application's vector table at `APP_ADDR` is invalid or empty.
3. The application did not start its FDCAN peripheral.
4. The bitrate or acceptance filters do not match the bus.

## Development

```bash
pip install -e .[socketcan,test]
pytest -v --cov=flasher --cov-report=term-missing
```

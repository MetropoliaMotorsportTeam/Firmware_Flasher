import argparse
import os
import subprocess
import sys
import time

from flasher.backends.base import CanBackend, CanBackendError, CanFrame
from flasher.cli import APP_ALIVE_ID_BY_BACKEND, build_backend
from flasher.protocol import CMD_ENTER_BOOTLOADER

SOCKETCAN_NET_DIR = "/sys/class/net"
TRIGGER_DATA = b"\xff"
POLL_INTERVAL_S = 0.1


def list_socketcan_interfaces(net_dir: str = SOCKETCAN_NET_DIR) -> list[tuple[str, str]]:
    interfaces = []
    for name in sorted(os.listdir(net_dir)):
        if not name.startswith(("can", "vcan")):
            continue
        with open(os.path.join(net_dir, name, "operstate")) as f:
            interfaces.append((name, f.read().strip()))
    return interfaces


def _ip_link_detail(name: str) -> str:
    return subprocess.run(["ip", "link", "show", name], capture_output=True, text=True).stdout.strip()


def list_canlib_channels() -> list[tuple[int, str, str, str]]:
    from canlib import canlib

    channels = []
    for index in range(canlib.getNumberOfChannels()):
        data = canlib.ChannelData(index)
        channels.append((index, data.channel_name, data.card_upc_no, data.card_serial_no))
    return channels


def _print_frame(frame: CanFrame) -> None:
    data = " ".join(f"{byte:02X}" for byte in frame.data)
    print(f"id=0x{frame.can_id:X} dlc={len(frame.data)} data={data}")


def listen(backend: CanBackend, duration_s: float | None) -> None:
    deadline = None if duration_s is None else time.monotonic() + duration_s
    while deadline is None or time.monotonic() < deadline:
        frame = backend.recv(timeout_s=POLL_INTERVAL_S)
        if frame is not None:
            _print_frame(frame)


def probe(backend: CanBackend, app_alive_id: int, duration_s: float) -> bool:
    backend.send(CMD_ENTER_BOOTLOADER, TRIGGER_DATA)
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        frame = backend.recv(timeout_s=POLL_INTERVAL_S)
        if frame is None:
            continue
        _print_frame(frame)
        if frame.can_id == app_alive_id:
            return True
    return False


def _add_bus_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", required=True, choices=sorted(APP_ALIVE_ID_BY_BACKEND))
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, required=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="can-diag")
    commands = parser.add_subparsers(dest="command", required=True)

    channels = commands.add_parser("channels", help="list available CAN interfaces or channels")
    channels.add_argument("--backend", required=True, choices=sorted(APP_ALIVE_ID_BY_BACKEND))
    channels.add_argument("--verbose", action="store_true", help="show the full ip link output (SocketCAN)")

    listen_parser = commands.add_parser("listen", help="print every frame seen on the bus")
    _add_bus_arguments(listen_parser)
    listen_parser.add_argument("--duration", type=float, help="seconds to listen, default until Ctrl-C")

    probe_parser = commands.add_parser(
        "probe", help="send the enter-bootloader trigger and wait for the application's alive ACK"
    )
    _add_bus_arguments(probe_parser)
    probe_parser.add_argument("--duration", type=float, default=5.0, help="seconds to wait, default 5")
    probe_parser.add_argument(
        "--app-id",
        type=lambda text: int(text, 0),
        help="application alive ACK ID, default depends on the backend",
    )

    return parser


def _print_channels(backend_name: str, verbose: bool) -> int:
    if backend_name == "socketcan":
        interfaces = list_socketcan_interfaces()
        if not interfaces:
            print("no CAN interfaces found")
            return 1
        for name, state in interfaces:
            print(f"{name}: {state}")
            if verbose:
                print(_ip_link_detail(name))
        return 0

    try:
        channels = list_canlib_channels()
    except Exception as e:
        print(f"error: could not query CANlib channels: {e}", file=sys.stderr)
        return 1
    if not channels:
        print("no CANlib channels found")
        return 1
    for index, name, upc, serial in channels:
        print(f"{index}. {name} ({upc} / {serial})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.command == "channels":
        return _print_channels(args.backend, args.verbose)

    try:
        backend = build_backend(args.backend, args.port, args.baud)
    except CanBackendError as e:
        print(f"error: could not open CAN interface: {e}", file=sys.stderr)
        return 1

    try:
        if args.command == "listen":
            listen(backend, args.duration)
            return 0
        app_id = args.app_id if args.app_id is not None else APP_ALIVE_ID_BY_BACKEND[args.backend]
        if probe(backend, app_id, args.duration):
            print("success: application alive ACK received")
            return 0
        print(
            "error: no application alive ACK within the timeout, see README 'Troubleshooting probe failures'",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        return 0
    except CanBackendError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        backend.shutdown()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

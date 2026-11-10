import argparse
import os
import sys
import tomllib

from flasher.backends.base import CanBackend, CanBackendError
from flasher.backends.socketcan import SocketCanBackend
from flasher.config import FlashConfig, load_config_file, merge_configs
from flasher.protocol import FlashSession, FlashSessionError

MAX_FIRMWARE_SIZE = 96 * 1024

# app alive-ACK ID after a successful jump. Backends disagree on the
# real value; kept as-is until confirmed.
APP_ALIVE_ID_BY_BACKEND = {"socketcan": 39, "canlib": 0x7D0}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flash")
    parser.add_argument("--backend", choices=["socketcan", "canlib"])
    parser.add_argument("--port")
    parser.add_argument("--baud", type=int)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--timeout-ms", type=int, dest="timeout_ms")
    parser.add_argument("--config")
    parser.add_argument("firmware_path")
    return parser


def _build_backend(backend_name: str, port: str, baud: int) -> CanBackend:
    if backend_name == "socketcan":
        return SocketCanBackend(channel=port, baud=baud)
    from flasher.backends.canlib import CanlibBackend  # pragma: no cover

    return CanlibBackend(channel=int(port), baud=baud)  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cli_config = FlashConfig(
        backend=args.backend,
        port=args.port,
        baud=args.baud,
        retries=args.retries,
        timeout_ms=args.timeout_ms,
        firmware_path=args.firmware_path,
    )

    if args.config:
        try:
            file_config = load_config_file(args.config)
        except (OSError, tomllib.TOMLDecodeError) as e:
            print(f"error: could not read config file {args.config}: {e}", file=sys.stderr)
            return 1
    else:
        file_config = FlashConfig(
            backend=None, port=None, baud=None, retries=None, timeout_ms=None, firmware_path=None
        )

    config = merge_configs(file_config, cli_config)

    missing = [
        name
        for name in ("backend", "port", "baud", "firmware_path")
        if getattr(config, name) is None
    ]
    if missing:
        print(parser.format_usage(), file=sys.stderr, end="")
        print(f"error: missing required value(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    if config.backend not in APP_ALIVE_ID_BY_BACKEND:
        print(f"error: unknown backend: {config.backend}", file=sys.stderr)
        return 1

    if not os.path.exists(config.firmware_path):
        print(f"error: firmware file not found: {config.firmware_path}", file=sys.stderr)
        return 1

    with open(config.firmware_path, "rb") as f:
        firmware = f.read()

    print(f"firmware size: {len(firmware)} bytes")

    if len(firmware) > MAX_FIRMWARE_SIZE:
        print(
            f"error: firmware size {len(firmware)} exceeds max size {MAX_FIRMWARE_SIZE}",
            file=sys.stderr,
        )
        return 1

    try:
        backend = _build_backend(config.backend, config.port, config.baud)
    except CanBackendError as e:
        print(f"error: could not open CAN interface: {e}", file=sys.stderr)
        return 1

    try:
        session = FlashSession(
            backend,
            app_alive_id=APP_ALIVE_ID_BY_BACKEND[config.backend],
            max_retries=config.retries if config.retries is not None else 5,
            timeout_ms=config.timeout_ms if config.timeout_ms is not None else 5000,
        )
        session.run(firmware)
    except (FlashSessionError, CanBackendError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        backend.shutdown()

    print("success: firmware flashed and application started")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

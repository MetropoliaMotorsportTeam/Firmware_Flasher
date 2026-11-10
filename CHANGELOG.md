# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shared protocol module (`flasher/protocol.py`) for firmware chunking
  and CRC computation, used by both backends instead of being
  duplicated per backend.
- `CanBackend` abstraction defining a common send/recv/shutdown
  interface for CAN backends.
- SocketCAN backend implementation. `recv` wraps CAN errors in
  `CanBackendError`.
- CANlib backend implementation, using CANlib's own bitrate constants
  instead of raw baud values for `setBusParams`.
- `FlashSession`, implementing the retry/ACK state machine against the
  bootloader protocol. Pending frames are flushed before each chunk
  send so a stale response isn't mistaken for the next chunk's ack.
- TOML configuration file support (`flasher/config.py`), merged with
  CLI flags (CLI wins).
- Non-interactive CLI entry point (`flash`). Missing required
  configuration, an invalid backend, a missing or malformed `--config`
  file, and a CAN error during a flash all print a clear error.
- `pyproject.toml` packaging with per-backend optional dependency
  groups (`socketcan`, `canlib`, `test`).

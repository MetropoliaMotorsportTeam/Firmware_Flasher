import time
import zlib

from flasher.backends.base import CanBackend

CHUNK_SIZE = 8
MAX_RETRIES = 5
TIMEOUT_MS = 5000

CMD_ENTER_BOOTLOADER = 0x02
CMD_DATA_CHUNK = 0x03
CMD_DONE_FLASHING = 0x04

RESP_READY_ACK = 0x7FE
RESP_RETRY_NACK = 0x7FF


def chunk_firmware(data: bytes, chunk_size: int = CHUNK_SIZE) -> list[bytes]:
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    if chunks and len(chunks[-1]) < chunk_size:
        chunks[-1] = chunks[-1] + b"\xff" * (chunk_size - len(chunks[-1]))
    return chunks


def compute_crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def build_done_payload(crc: int) -> list[int]:
    return [0xAA, 0xFF] + list(crc.to_bytes(4, "big")) + [0x00, 0x00]


class FlashSessionError(Exception):
    pass


class FlashSession:
    def __init__(
        self,
        backend: CanBackend,
        app_alive_id: int,
        max_retries: int = MAX_RETRIES,
        timeout_ms: int = TIMEOUT_MS,
    ):
        self._backend = backend
        self._app_alive_id = app_alive_id
        self._max_retries = max_retries
        self._timeout_ms = timeout_ms

    def _flush(self) -> None:
        while self._backend.recv(timeout_s=0) is not None:
            pass

    def _wait_for(self, expected_ids: set[int], timeout_ms: int) -> int | None:
        end_time = time.time() + (timeout_ms / 1000.0)
        while time.time() < end_time:
            frame = self._backend.recv(timeout_s=0.05)
            if frame is None:
                continue
            if frame.can_id in expected_ids:
                return frame.can_id
        return None

    def run(self, firmware: bytes) -> None:
        self._backend.send(CMD_ENTER_BOOTLOADER, b"\x00")
        if self._wait_for({RESP_READY_ACK}, self._timeout_ms) != RESP_READY_ACK:
            raise FlashSessionError("no response from bootloader")

        running_crc = compute_crc(firmware)
        for chunk in chunk_firmware(firmware, CHUNK_SIZE):
            acked = False
            for _ in range(self._max_retries):
                self._flush()
                self._backend.send(CMD_DATA_CHUNK, chunk)
                resp = self._wait_for({RESP_READY_ACK, RESP_RETRY_NACK}, self._timeout_ms)
                if resp == RESP_READY_ACK:
                    acked = True
                    break
            if not acked:
                raise FlashSessionError(f"chunk failed after {self._max_retries} retries")

        done_payload = bytes(build_done_payload(running_crc))
        self._backend.send(CMD_DONE_FLASHING, done_payload)
        resp = self._wait_for({self._app_alive_id, RESP_RETRY_NACK}, self._timeout_ms)
        if resp == RESP_RETRY_NACK:
            raise FlashSessionError("bootloader reported a CRC mismatch")
        if resp != self._app_alive_id:
            raise FlashSessionError("no alive-ACK from the application after flashing")

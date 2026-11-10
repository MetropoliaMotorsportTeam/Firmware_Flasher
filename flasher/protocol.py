import zlib

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

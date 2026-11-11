import pytest

from flasher.backends.base import CanFrame
from flasher.protocol import (
    CMD_DATA_CHUNK,
    CMD_DONE_FLASHING,
    FlashSession,
    FlashSessionError,
    RESP_READY_ACK,
    RESP_RETRY_NACK,
)
from tests.conftest import FakeCanBackend as FakeBackend


def test_run_succeeds_with_all_acks():
    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            CanFrame(2000, b""),  # app alive-ack, no separate done-ack on the wire
        ]
    )
    session = FlashSession(backend, app_alive_id=2000)
    session.run(b"\x01\x02")  # 1 chunk after padding
    assert len(backend.sent) >= 2  # enter-bootloader + at least one data chunk


def test_run_raises_when_bootloader_never_acks():
    backend = FakeBackend([])
    session = FlashSession(backend, app_alive_id=2000)
    with pytest.raises(FlashSessionError, match="bootloader"):
        session.run(b"\x01")


def test_run_raises_after_max_retries_on_a_chunk():
    backend = FakeBackend([CanFrame(RESP_READY_ACK, b"")])  # only the enter-bootloader ACK
    session = FlashSession(backend, app_alive_id=2000, max_retries=2, timeout_ms=10)
    with pytest.raises(FlashSessionError, match="retries"):
        session.run(b"\x01")


def test_run_raises_on_nack_after_done_payload():
    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            CanFrame(RESP_RETRY_NACK, b""),  # done-payload NACK
        ]
    )
    session = FlashSession(backend, app_alive_id=2000)
    with pytest.raises(FlashSessionError, match="CRC"):
        session.run(b"\x01")


def test_run_raises_when_no_alive_ack_after_flashing():
    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            # nothing for the alive-ACK wait after done-flashing
        ]
    )
    session = FlashSession(backend, app_alive_id=2000, timeout_ms=10)
    with pytest.raises(FlashSessionError, match="alive"):
        session.run(b"\x01")


def test_run_computes_crc_over_padded_firmware_not_raw():
    firmware = b"\x01\x02\x03"  # not a multiple of CHUNK_SIZE (8)
    padded = firmware + b"\xff" * 5
    from flasher.protocol import compute_crc

    expected_crc = compute_crc(padded)

    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            CanFrame(2000, b""),  # app alive-ack
        ]
    )
    session = FlashSession(backend, app_alive_id=2000)
    session.run(firmware)

    done_call = [call for call in backend.sent if call[0] == CMD_DONE_FLASHING][0]
    sent_crc_bytes = bytes(done_call[1][2:6])
    assert sent_crc_bytes == expected_crc.to_bytes(4, "big")


def test_run_flushes_pending_frames_before_each_chunk_send():
    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            CanFrame(2000, b""),  # app alive-ack
        ]
    )
    session = FlashSession(backend, app_alive_id=2000)
    session.run(b"\x01\x02")

    chunk_send_indices = [i for i, call in enumerate(backend.calls) if call[0] == "send" and call[1] == CMD_DATA_CHUNK]
    assert chunk_send_indices, "expected at least one data chunk send"
    for i in chunk_send_indices:
        assert backend.calls[i - 1] == ("recv", 0), "expected a non-blocking drain right before each chunk send"


def test_run_discards_a_stale_pending_frame_before_chunk_send():
    backend = FakeBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # the real chunk ack
            CanFrame(2000, b""),  # app alive-ack
        ],
        pending=[CanFrame(RESP_RETRY_NACK, b"")],  # stale, must not be read as this chunk's ack
    )
    session = FlashSession(backend, app_alive_id=2000)
    session.run(b"\x01\x02")
    assert backend.pending == []
    assert backend.responses == []

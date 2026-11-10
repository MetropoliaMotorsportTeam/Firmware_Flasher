from flasher.protocol import chunk_firmware, compute_crc, build_done_payload


def test_chunk_firmware_exact_multiple():
    data = bytes(range(16))
    chunks = chunk_firmware(data, chunk_size=8)
    assert chunks == [bytes(range(8)), bytes(range(8, 16))]


def test_chunk_firmware_pads_last_chunk():
    data = bytes(range(10))
    chunks = chunk_firmware(data, chunk_size=8)
    assert chunks[-1] == bytes(range(8, 10)) + b"\xff" * 6


def test_compute_crc_matches_zlib():
    import zlib

    data = b"123456789"
    assert compute_crc(data) == zlib.crc32(data) & 0xFFFFFFFF


def test_compute_crc_matches_bootloader_known_good_vector():
    # the bootloader's own known-good CRC-32 check value
    assert compute_crc(b"123456789") == 0xCBF43926


def test_build_done_payload_format():
    payload = build_done_payload(0xCBF43926)
    assert payload == [0xAA, 0xFF, 0xCB, 0xF4, 0x39, 0x26, 0x00, 0x00]

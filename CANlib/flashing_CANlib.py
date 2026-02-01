import zlib
import os
import time
from canlib import canlib

# ---------------- Configuration ----------------

# TODO: Add proper CAN filters
# TODO: Add sequence numbers
# TODO: Or redesign ACK/NACK so retries are bulletproof

CHANNEL_NUMBER = 0
BAUD_RATE = canlib.canBITRATE_1M

CMD_ENTER_BOOTLOADER = 0x02
CMD_DATA_CHUNK = 0x03
CMD_DONE_FLASHING = 0x04

RESP_READY_ACK = 0x7FE  # 2046
RESP_RETRY_NACK = 0x7FF  # 2047
TEST_ID = 0x7D0  # 2000
VALID_IDS = {RESP_READY_ACK, RESP_RETRY_NACK, TEST_ID}

CHUNK_SIZE = 8
MAX_RETRIES = 5
TIMEOUT_MS = 5000
MAX_SIZE = 96 * 1024

# ------------------------------------------------


def send_message(ch, can_id, data=None):
    if data is None:
        data = [0x00]
    try:
        ch.write(can_id, data, flag=0)
        return True
    except Exception as e:
        print(f"[TX ERROR] ID 0x{can_id:X}: {e}")
        return False


def flush_rx(ch):
    try:
        while True:
            ch.read(timeout=0)
    except canlib.canNoMsg:
        pass


def wait_app(ch, timeout_ms):
    print("Waiting for response")
    end_time = time.time() + (timeout_ms / 1000.0)

    while time.time() < end_time:
        try:
            msg = ch.read(timeout=50)
            print(f"id={msg.id}, flags={msg.flags}, dlc={msg.dlc}")

            if msg.id not in VALID_IDS:
                continue

            elif msg.id == TEST_ID:
                return "ACK"
            elif msg.id == RESP_RETRY_NACK:
                return "NACK"

        except canlib.canNoMsg:
            continue
        except canlib.canMSG_ERROR_FRAME:
            continue
        except canlib.canError as e:
            print(f"CAN Error: {e}")
            break

    return None


def wait_for_response(ch, send_time, timeout_ms):
    print("Waiting for response")
    end_time = time.time() + (timeout_ms / 1000.0)

    while time.time() < end_time:
        try:
            msg = ch.read(timeout=50)
            print(f"id={msg.id}, flags={msg.flags}, dlc={msg.dlc}")

            if msg.id not in VALID_IDS:
                continue

            if msg.id == RESP_READY_ACK:
                return "ACK"
            elif msg.id == TEST_ID:
                return "ACK"
            elif msg.id == RESP_RETRY_NACK:
                return "NACK"

        except canlib.canNoMsg:
            continue
        except canlib.canMSG_ERROR_FRAME:
            continue
        except canlib.canError as e:
            print(f"CAN Error: {e}")
            break

    return None


def load_bin_file(file_path):
    if not os.path.exists(file_path):
        print("File not found.")
        return None

    with open(file_path, "rb") as f:
        data = f.read()

    if len(data) > MAX_SIZE:
        print(f"Error: Binary size {len(data)} exceeds limit {MAX_SIZE}")
        return None

    return data


def flash_stm32_protocol(channel, baud, file_path):

    print("\n--- STM32 CAN Flash Tool ---")

    # Open CAN
    try:
        ch = canlib.openChannel(channel, canlib.canOPEN_EXCLUSIVE)
        ch.setBusParams(baud)
        ch.busOn()
    except Exception as e:
        print(f"CAN init failed: {e}")
        return

    try:
        firmware = load_bin_file(file_path)
        if firmware is None:
            return

        total_bytes = len(firmware)
        total_chunks = (total_bytes + CHUNK_SIZE - 1) // CHUNK_SIZE
        crc32 = zlib.crc32(firmware) & 0xFFFFFFFF

        print(f"Firmware size: {total_bytes} bytes")
        print(f"CRC32: 0x{crc32:08X}")
        print(f"Chunks: {total_chunks}")

        # ---- Enter Bootloader ----
        print("\n-> Entering Bootloader...")
        send_time = time.time()
        send_message(ch, CMD_ENTER_BOOTLOADER)

        if wait_for_response(ch, send_time, 5000) != "ACK":
            print("ERROR: No bootloader response")
            return

        print("<- Bootloader Ready")

        # ---- Send Firmware ----
        print("\n--- Flashing ---")

        for idx in range(total_chunks):
            start = idx * CHUNK_SIZE
            chunk = firmware[start : start + CHUNK_SIZE]

            if len(chunk) < CHUNK_SIZE:
                chunk += b"\xff" * (CHUNK_SIZE - len(chunk))

            retries = 0
            while retries < MAX_RETRIES:
                send_time = time.time()  # Unused
                flush_rx(ch)
                send_message(ch, CMD_DATA_CHUNK, list(chunk))

                resp = wait_for_response(ch, send_time, TIMEOUT_MS)

                if resp == "ACK":
                    break

                retries += 1
                print(
                    f"[!] Retry chunk {idx + 1}/{total_chunks} ({retries}/{MAX_RETRIES})"
                )

            if retries == MAX_RETRIES:
                print("CRITICAL ERROR: Flash failed")
                return

            if idx % 10 == 0:
                print(f"\rProgress: {idx + 1}/{total_chunks}", end="")

        print(f"\rProgress: {total_chunks}/{total_chunks}")
        print("All data sent")

        # ---- Finish ----
        crc_bytes = crc32.to_bytes(4, "big")
        done_payload = [0xAA, 0xFF] + list(crc_bytes) + [0x00, 0x00]

        print("\n-> Finalizing...")
        send_time = time.time()
        send_message(ch, CMD_DONE_FLASHING, done_payload)

        if wait_app(ch, 2000) == "ACK":
            print("SUCCESS: Application started")
        else:
            print("WARNING: No final ACK")

    finally:
        ch.busOff()
        ch.close()


if __name__ == "__main__":
    FILE_PATH = input("Path to .bin file: ").strip()
    FILE_PATH = "Application.bin"

    try:
        MAX_SIZE = int(input("Max size (KB): ")) << 10
    except ValueError:
        pass

    flash_stm32_protocol(CHANNEL_NUMBER, BAUD_RATE, FILE_PATH)

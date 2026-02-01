import can
import time

# --- Configuration ---
CHANNEL = "can0"
CMD_ENTER_BOOTLOADER = 0x02
DATA_TRIGGER = 0xFF
RESP_ACK = 2000

TIMEOUT_S = 5.0


def run_test():
    print(f"Opening SocketCAN interface {CHANNEL}...")

    try:
        bus = can.interface.Bus(channel=CHANNEL, interface="socketcan")
    except Exception as e:
        print(f"Failed to open CAN interface: {e}")
        return

    print(
        f"Sending Jump Command (ID: 0x{CMD_ENTER_BOOTLOADER:X}, Data: 0x{DATA_TRIGGER:X})..."
    )

    msg = can.Message(
        arbitration_id=CMD_ENTER_BOOTLOADER, data=[DATA_TRIGGER], is_extended_id=False
    )

    try:
        bus.send(msg)
    except can.CanError as e:
        print(f"TX failed: {e}")
        return

    print(f"Command sent. Waiting for Application ACK (ID {RESP_ACK})...")

    deadline = time.time() + TIMEOUT_S
    success = False

    while time.time() < deadline:
        rx = bus.recv(timeout=0.1)
        if rx is None:
            continue

        print(f"RX: id=0x{rx.arbitration_id:X}, dlc={rx.dlc}, data={list(rx.data)}")

        if rx.arbitration_id == RESP_ACK:
            print("SUCCESS: Received ACK from Application!")
            success = True
            break

    if not success:
        print("FAILED: No response from Application.")
        print("Possible causes:")
        print("  1. System_Jump failed")
        print("  2. APP vector table invalid")
        print("  3. Application FDCAN not started")
        print("  4. Wrong bitrate or filters")

    bus.shutdown()


if __name__ == "__main__":
    run_test()

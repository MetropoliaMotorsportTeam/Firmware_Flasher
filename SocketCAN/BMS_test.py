import can
import time


CHANNEL = "can0"
BAUD_RATE = 1000000
CMD_CHANGE_CONF = 0x21
DATA_TRIGGER = 1
RESP_ACK = 0x12

TIMEOUT_S = 5.0


def run_test():
    print(f"Opening CAN channel {CHANNEL}...")

    try:
        bus = can.interface.Bus(channel=CHANNEL, interface="socketcan")
    except Exception as e:
        print(f"Failed to open CAN interface: {e}")
        return

    print(f"Sending Config Change Command (ID: 0x{CMD_CHANGE_CONF})")

    msg = can.Message(
        arbitration_id=CMD_CHANGE_CONF, data=[DATA_TRIGGER], is_extended_id=False
    )

    try:
        bus.send(msg)
    except can.CanError as e:
        print(f"TX failed: {e}")
        return
    print("Command sent. Waiting for BMS to send response")

    deadline = time.time() + TIMEOUT_S
    success = False

    while time.time() < deadline:
        rx = bus.recv(timeout=0.1)
        if rx is None:
            continue

        print(f"RX: id=0x{rx.arbitration_id:X}, dlc={rx.dlc}, data={list(rx.data)}")

        if rx.arbitration_id == RESP_ACK:
            print("SUCCESS: Received ACK from BMS!")
            success = True
            break

    if not success:
        print("FAILED: No response from BMS.")

    bus.shutdown()


if __name__ == "__main__":
    run_test()

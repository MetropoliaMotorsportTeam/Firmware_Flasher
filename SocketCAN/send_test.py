import can
import time


CHANNEL = "can0"
BAUD_RATE = 1000000  # need to manually set baudrate when running on linux
CMD_TO_SEND = 0x20
DATA_TRIGGER = [2, 0]
RESP_ACK = 32

TIMEOUT_S = 10.0


def run_test():
    print(f"Opening CAN channel {CHANNEL}...")

    try:
        bus = can.interface.Bus(channel=CHANNEL, interface="socketcan")
    except Exception as e:
        print(f"Failed to open CAN interface: {e}")
        return

    print(f"Sending Command, ID: {hex(CMD_TO_SEND)}")

    msg = can.Message(
        arbitration_id=CMD_TO_SEND, data=DATA_TRIGGER, is_extended_id=False
    )

    try:
        bus.send(msg)
    except can.CanError as e:
        print(f"TX failed: {e}")
        return
    print("Command sent. Waiting for response.")

    deadline = time.time() + TIMEOUT_S
    success = False

    while time.time() < deadline:
        rx = bus.recv(timeout=0.1)
        if rx is None:
            continue

        print(f"RX: id=0x{rx.arbitration_id:X}, dlc={rx.dlc}, data={list(rx.data)}")

        if rx.arbitration_id == RESP_ACK:
            print("SUCCESS: Received ACK.")
            success = True
            break

    if not success:
        print("FAILED: No response.")

    bus.shutdown()


if __name__ == "__main__":
    run_test()

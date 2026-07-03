from canlib import canlib
import time


CHANNEL_NUMBER = 0
BAUD_RATE = canlib.canBITRATE_1M
CMD_TO_SEND = 0x76C
DATA_TRIGGER = [1]
RESP_ACK = 0x12


def run_test():
    print(f"Opening CAN channel {CHANNEL_NUMBER}...")
    try:
        ch = canlib.openChannel(CHANNEL_NUMBER, canlib.canOPEN_EXCLUSIVE)
        ch.setBusParams(BAUD_RATE)
        ch.busOn()
    except Exception as e:
        print(f"Failed to open CAN: {e}")
        return

    print(f"Sending Command, ID: {hex(CMD_TO_SEND)}")
    ch.write(CMD_TO_SEND, DATA_TRIGGER, flag=0)
    print("Command sent. Waiting for response.")

    timeout = time.time() + 5.0
    success = False

    while time.time() < timeout:
        try:
            # Short poll for messages
            msg = ch.read(timeout=100)
            if msg.id == RESP_ACK:
                print("SUCCESS: Received ACK.")
                print(f"Data received: {list(msg.data)}")
                success = True
                break
        except canlib.canNoMsg:
            continue
        except Exception as e:
            print(f"Read error: {e}")
            break

    if not success:
        print("FAILED: No response.")

    ch.busOff()
    ch.close()


if __name__ == "__main__":
    run_test()

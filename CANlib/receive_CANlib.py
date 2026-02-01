from canlib import canlib
import time

# --- Configuration ---
CHANNEL_NUMBER = 0
BAUD_RATE = canlib.canBITRATE_1M

CMD_ENTER_BOOTLOADER = 0x02  # ID to trigger the jump
DATA_TRIGGER = 0xFF  # Data byte to trigger the jump logic
RESP_ACK = 0x7FE  # (2046) The ID the APP sends upon successful start


def run_test():
    print(f"Opening CAN channel {CHANNEL_NUMBER}...")
    try:
        ch = canlib.openChannel(CHANNEL_NUMBER, canlib.canOPEN_EXCLUSIVE)
        ch.setBusParams(BAUD_RATE)
        ch.busOn()
    except Exception as e:
        print(f"Failed to open CAN: {e}")
        return

    print(
        f"Sending Jump Command (ID: 0x{CMD_ENTER_BOOTLOADER:X}, Data: 0x{DATA_TRIGGER:X})..."
    )

    # Send message to trigger the bootloader jump
    ch.write(CMD_ENTER_BOOTLOADER, [DATA_TRIGGER], flag=0)

    print("Command sent. Waiting for Application to start and send ACK (ID 2046)...")

    # Increased timeout to 5.0s to allow for STM32 jump, app init, and CAN start
    timeout = time.time() + 5.0
    success = False

    while time.time() < timeout:
        try:
            # Short poll for messages
            msg = ch.read(timeout=100)
            if msg.id == RESP_ACK:
                print("SUCCESS: Received ACK from Application!")
                print(f"Data received: {list(msg.data)}")
                success = True
                break
        except canlib.canNoMsg:
            continue
        except Exception as e:
            print(f"Read error: {e}")
            break

    if not success:
        print("FAILED: No response from Application. Potential issues:")
        print("1. System_Jump failed or APP_ADDR is empty.")
        print("2. Application did not initialize FDCAN correctly.")
        print("3. Application is not sending ID 2046.")

    ch.busOff()
    ch.close()


if __name__ == "__main__":
    run_test()

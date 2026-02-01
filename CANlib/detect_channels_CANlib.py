import os
import time
from canlib import canlib

CHANNEL_NUMS = [0, 1]
BAUD_RATE = canlib.canBITRATE_1M


def detect_channel(channel, baud):
    print("Detecting channels")
    try:
        num_channels = canlib.getNumberOfChannels()
        print("Found %d channels" % num_channels)

        for channel in range(0, num_channels):
            chdata = canlib.ChannelData(channel)

            print("%d. %s (%s / %s)" % (
                channel,
                chdata.channel_name,
                chdata.card_upc_no,
                chdata.card_serial_no)
            )
        return True

    except Exception as e:
        print(f"CAN Init Failed: {e}")
        return False


if __name__ == "__main__":
    # for channel in CHANNEL_NUMS:
    #     if detect_channel(channel, BAUD_RATE):
    #         print(f"found channel {channel}")
    #     else:
    #         print(f"{channel} does not exist")
    # Try channel 1 if channel 0 does not work
    detect_channel(0, BAUD_RATE)


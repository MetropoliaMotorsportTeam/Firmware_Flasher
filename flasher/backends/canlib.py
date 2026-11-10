from canlib import canlib

from flasher.backends.base import CanBackend, CanBackendError, CanFrame

BAUD_TO_CANLIB_CONST_NAME = {
    1000000: "canBITRATE_1M",
    500000: "canBITRATE_500K",
    250000: "canBITRATE_250K",
    125000: "canBITRATE_125K",
}


def _resolve_bitrate(baud: int):
    const_name = BAUD_TO_CANLIB_CONST_NAME.get(baud)
    if const_name is None:
        raise CanBackendError(f"unsupported baud rate for CANlib: {baud}")
    return getattr(canlib, const_name)


class CanlibBackend(CanBackend):
    def __init__(self, channel: int, baud: int):
        try:
            self._channel = canlib.openChannel(channel, canlib.canOPEN_EXCLUSIVE)
            self._channel.setBusParams(_resolve_bitrate(baud))
            self._channel.busOn()
        except CanBackendError:
            raise
        except Exception as e:
            raise CanBackendError(str(e)) from e

    def send(self, can_id: int, data: bytes) -> bool:
        try:
            self._channel.write(can_id, list(data), flag=0)
            return True
        except canlib.canError as e:
            raise CanBackendError(str(e)) from e

    def recv(self, timeout_s: float) -> CanFrame | None:
        try:
            msg = self._channel.read(timeout=int(timeout_s * 1000))
            return CanFrame(can_id=msg.id, data=bytes(msg.data))
        except canlib.canNoMsg:
            return None
        except canlib.canMSG_ERROR_FRAME:
            return None

    def shutdown(self) -> None:
        self._channel.busOff()
        self._channel.close()

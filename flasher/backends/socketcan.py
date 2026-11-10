import can

from flasher.backends.base import CanBackend, CanBackendError, CanFrame


class SocketCanBackend(CanBackend):
    def __init__(self, channel: str, baud: int, interface: str = "socketcan"):
        try:
            self._bus = can.interface.Bus(channel=channel, interface=interface, bitrate=baud)
        except Exception as e:
            raise CanBackendError(str(e)) from e

    def send(self, can_id: int, data: bytes) -> bool:
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
            self._bus.send(msg)
            return True
        except can.CanError as e:
            raise CanBackendError(str(e)) from e

    def recv(self, timeout_s: float) -> CanFrame | None:
        try:
            msg = self._bus.recv(timeout=timeout_s)
        except can.CanError as e:
            raise CanBackendError(str(e)) from e
        if msg is None:
            return None
        return CanFrame(can_id=msg.arbitration_id, data=bytes(msg.data))

    def shutdown(self) -> None:
        self._bus.shutdown()

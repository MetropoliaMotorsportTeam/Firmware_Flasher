import pytest

from flasher.backends.socketcan import SocketCanBackend


def test_send_and_recv_roundtrip_on_virtual_bus():
    # virtual bus doesn't echo a sender's own frames, so use two backends
    sender = SocketCanBackend(channel="test-virtual", baud=1000000, interface="virtual")
    receiver = SocketCanBackend(channel="test-virtual", baud=1000000, interface="virtual")
    try:
        assert sender.send(0x02, b"\x00") is True
        frame = receiver.recv(timeout_s=1.0)
        assert frame is not None
        assert frame.can_id == 0x02
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_recv_returns_none_on_timeout():
    backend = SocketCanBackend(channel="test-virtual-2", baud=1000000, interface="virtual")
    try:
        assert backend.recv(timeout_s=0.05) is None
    finally:
        backend.shutdown()


def test_init_wraps_open_failure_in_can_backend_error(monkeypatch):
    import can

    from flasher.backends.base import CanBackendError

    def raise_error(*args, **kwargs):
        raise can.CanError("no such interface")

    monkeypatch.setattr(can.interface, "Bus", raise_error)
    with pytest.raises(CanBackendError):
        SocketCanBackend(channel="not-a-real-channel", baud=1000000)


def test_recv_wraps_can_error_in_can_backend_error(monkeypatch):
    import can

    from flasher.backends.base import CanBackendError

    backend = SocketCanBackend(channel="test-virtual-4", baud=1000000, interface="virtual")
    try:

        def raise_error(*args, **kwargs):
            raise can.CanError("bus off")

        monkeypatch.setattr(backend._bus, "recv", raise_error)
        with pytest.raises(CanBackendError):
            backend.recv(timeout_s=0.05)
    finally:
        backend.shutdown()


def test_send_wraps_can_error_in_can_backend_error(monkeypatch):
    import can

    from flasher.backends.base import CanBackendError

    backend = SocketCanBackend(channel="test-virtual-3", baud=1000000, interface="virtual")
    try:

        def raise_error(*args, **kwargs):
            raise can.CanError("bus off")

        monkeypatch.setattr(backend._bus, "send", raise_error)
        with pytest.raises(CanBackendError):
            backend.send(0x02, b"\x00")
    finally:
        backend.shutdown()

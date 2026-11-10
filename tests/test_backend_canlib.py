import pytest

pytest.importorskip("canlib")

from unittest.mock import MagicMock, patch

from flasher.backends.base import CanBackendError
from flasher.backends.canlib import CanlibBackend


def test_init_opens_channel_sets_params_and_busses_on():
    fake_channel = MagicMock()
    with patch("flasher.backends.canlib.canlib.openChannel", return_value=fake_channel) as open_mock:
        CanlibBackend(channel=0, baud=1000000)
    open_mock.assert_called_once()
    fake_channel.setBusParams.assert_called_once_with(1000000)
    fake_channel.busOn.assert_called_once()


def test_init_wraps_open_failure_in_can_backend_error():
    with patch("flasher.backends.canlib.canlib.openChannel", side_effect=Exception("no driver")):
        with pytest.raises(CanBackendError):
            CanlibBackend(channel=0, baud=1000000)


def test_shutdown_calls_bus_off_and_close():
    fake_channel = MagicMock()
    with patch("flasher.backends.canlib.canlib.openChannel", return_value=fake_channel):
        backend = CanlibBackend(channel=0, baud=1000000)
    backend.shutdown()
    fake_channel.busOff.assert_called_once()
    fake_channel.close.assert_called_once()

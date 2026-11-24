import sys
import types

from flasher.backends.base import CanBackendError, CanFrame
from flasher.diagnostics import (
    list_canlib_channels,
    list_socketcan_interfaces,
    listen,
    main,
    probe,
)
from tests.conftest import FakeCanBackend


def test_list_socketcan_interfaces_reports_can_and_vcan_with_state(tmp_path):
    for name, state in [("can0", "up"), ("vcan1", "down"), ("eth0", "up")]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "operstate").write_text(state + "\n")

    assert list_socketcan_interfaces(net_dir=str(tmp_path)) == [("can0", "up"), ("vcan1", "down")]


def test_list_socketcan_interfaces_empty_when_no_can_devices(tmp_path):
    (tmp_path / "eth0").mkdir()
    (tmp_path / "eth0" / "operstate").write_text("up\n")

    assert list_socketcan_interfaces(net_dir=str(tmp_path)) == []


def _install_fake_canlib_channels(monkeypatch, channels):
    canlib_inner = types.SimpleNamespace(
        getNumberOfChannels=lambda: len(channels),
        ChannelData=lambda index: channels[index],
    )
    canlib_pkg = types.ModuleType("canlib")
    canlib_pkg.canlib = canlib_inner
    monkeypatch.setitem(sys.modules, "canlib", canlib_pkg)
    monkeypatch.setitem(sys.modules, "canlib.canlib", canlib_inner)


def _fake_channel(name, upc, serial):
    return types.SimpleNamespace(channel_name=name, card_upc_no=upc, card_serial_no=serial)


def test_list_canlib_channels_returns_index_name_upc_and_serial(monkeypatch):
    _install_fake_canlib_channels(
        monkeypatch,
        [_fake_channel("Kvaser Leaf", "73-30130", "12345"), _fake_channel("Kvaser Hybrid", "73-30131", "67890")],
    )

    assert list_canlib_channels() == [
        (0, "Kvaser Leaf", "73-30130", "12345"),
        (1, "Kvaser Hybrid", "73-30131", "67890"),
    ]


def test_listen_prints_each_received_frame(capsys):
    backend = FakeCanBackend([CanFrame(0x123, b"\x01\x02"), CanFrame(0x7FE, b"")])

    listen(backend, duration_s=0.05)

    out = capsys.readouterr().out
    assert "id=0x123 dlc=2 data=01 02" in out
    assert "id=0x7FE dlc=0" in out


def test_probe_sends_enter_bootloader_trigger_and_returns_true_on_app_ack(capsys):
    backend = FakeCanBackend([CanFrame(2000, b"")])

    assert probe(backend, app_alive_id=2000, duration_s=0.05) is True
    assert backend.sent == [(0x02, b"\xff")]


def test_probe_returns_false_when_no_app_ack_arrives():
    backend = FakeCanBackend([])

    assert probe(backend, app_alive_id=2000, duration_s=0.05) is False


def test_main_channels_socketcan_lists_interfaces(capsys, monkeypatch):
    monkeypatch.setattr("flasher.diagnostics.list_socketcan_interfaces", lambda: [("can0", "up")])

    assert main(["channels", "--backend", "socketcan"]) == 0
    assert "can0: up" in capsys.readouterr().out


def test_main_channels_socketcan_errors_when_none_found(capsys, monkeypatch):
    monkeypatch.setattr("flasher.diagnostics.list_socketcan_interfaces", lambda: [])

    assert main(["channels", "--backend", "socketcan"]) == 1
    assert "no CAN interfaces" in capsys.readouterr().out


def test_main_channels_canlib_lists_channels(capsys, monkeypatch):
    _install_fake_canlib_channels(monkeypatch, [_fake_channel("Kvaser Leaf", "73-30130", "12345")])

    assert main(["channels", "--backend", "canlib"]) == 0
    assert "0. Kvaser Leaf (73-30130 / 12345)" in capsys.readouterr().out


def test_main_listen_runs_for_given_duration(capsys, monkeypatch):
    fake_backend = FakeCanBackend([CanFrame(0x7FE, b"")])
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda backend, port, baud: fake_backend)

    code = main(["listen", "--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--duration", "0.05"])

    assert code == 0
    assert "id=0x7FE" in capsys.readouterr().out


def test_main_probe_reports_success_when_app_acks(capsys, monkeypatch):
    fake_backend = FakeCanBackend([CanFrame(39, b"")])
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda backend, port, baud: fake_backend)

    code = main(["probe", "--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--duration", "0.05"])

    assert code == 0
    assert "success" in capsys.readouterr().out.lower()


def test_main_probe_reports_failure_when_no_ack(capsys, monkeypatch):
    fake_backend = FakeCanBackend([])
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda backend, port, baud: fake_backend)

    code = main(["probe", "--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--duration", "0.05"])

    assert code == 1
    assert "no application" in capsys.readouterr().err.lower()


def test_main_channels_canlib_reports_query_failure(capsys, monkeypatch):
    def no_driver():
        raise RuntimeError("no driver")

    canlib_inner = types.SimpleNamespace(getNumberOfChannels=no_driver)
    canlib_pkg = types.ModuleType("canlib")
    canlib_pkg.canlib = canlib_inner
    monkeypatch.setitem(sys.modules, "canlib", canlib_pkg)
    monkeypatch.setitem(sys.modules, "canlib.canlib", canlib_inner)

    assert main(["channels", "--backend", "canlib"]) == 1
    assert "no driver" in capsys.readouterr().err


def test_main_channels_canlib_errors_when_no_channels(capsys, monkeypatch):
    _install_fake_canlib_channels(monkeypatch, [])

    assert main(["channels", "--backend", "canlib"]) == 1
    assert "no CANlib channels" in capsys.readouterr().out


def test_main_errors_when_interface_cannot_open(capsys, monkeypatch):
    def refuse(backend, port, baud):
        raise CanBackendError("no such device")

    monkeypatch.setattr("flasher.diagnostics.build_backend", refuse)

    code = main(["listen", "--backend", "socketcan", "--port", "can9", "--baud", "1000000", "--duration", "0.05"])

    assert code == 1
    assert "could not open CAN interface" in capsys.readouterr().err


class _InterruptedBackend(FakeCanBackend):
    def __init__(self, error):
        super().__init__([])
        self.error = error
        self.shut_down = False

    def recv(self, timeout_s):
        raise self.error

    def shutdown(self):
        self.shut_down = True


def test_main_listen_exits_cleanly_on_ctrl_c(monkeypatch):
    backend = _InterruptedBackend(KeyboardInterrupt())
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda b, p, d: backend)

    assert main(["listen", "--backend", "socketcan", "--port", "can0", "--baud", "1000000"]) == 0
    assert backend.shut_down


def test_main_probe_reports_bus_error(capsys, monkeypatch):
    backend = _InterruptedBackend(CanBackendError("bus off"))
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda b, p, d: backend)

    code = main(["probe", "--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--duration", "0.05"])

    assert code == 1
    assert "bus off" in capsys.readouterr().err
    assert backend.shut_down


def test_main_probe_app_id_flag_overrides_backend_default(capsys, monkeypatch):
    fake_backend = FakeCanBackend([CanFrame(0x7D0, b"")])
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda backend, port, baud: fake_backend)

    code = main(
        ["probe", "--backend", "socketcan", "--port", "can0", "--baud", "1000000",
         "--app-id", "0x7D0", "--duration", "0.05"]
    )

    assert code == 0


def test_main_probe_failure_points_to_readme(capsys, monkeypatch):
    fake_backend = FakeCanBackend([])
    monkeypatch.setattr("flasher.diagnostics.build_backend", lambda backend, port, baud: fake_backend)

    main(["probe", "--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--duration", "0.05"])

    assert "README" in capsys.readouterr().err


def test_main_channels_socketcan_verbose_shows_ip_link_detail(capsys, monkeypatch):
    monkeypatch.setattr("flasher.diagnostics.list_socketcan_interfaces", lambda: [("can0", "up")])

    class _Completed:
        stdout = "4: can0: <NOARP,UP,LOWER_UP> mtu 16\n    link/can bitrate 1000000"

    monkeypatch.setattr("flasher.diagnostics.subprocess.run", lambda *a, **k: _Completed())

    assert main(["channels", "--backend", "socketcan", "--verbose"]) == 0
    out = capsys.readouterr().out
    assert "can0: up" in out
    assert "bitrate 1000000" in out

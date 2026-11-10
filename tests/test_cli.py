from flasher.backends.base import CanFrame
from flasher.cli import main
from flasher.protocol import RESP_READY_ACK
from tests.conftest import FakeCanBackend


def test_main_errors_when_backend_missing(capsys):
    code = main(["--port", "can0", "--baud", "1000000", "fw.bin"])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "backend" in err
    assert "usage" in err


def test_main_errors_when_firmware_file_missing(capsys, tmp_path):
    missing = tmp_path / "nope.bin"
    code = main(["--backend", "socketcan", "--port", "can0", "--baud", "1000000", str(missing)])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "not found" in err or "no such file" in err


def test_main_errors_when_firmware_exceeds_max_size(capsys, tmp_path, monkeypatch):
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * 100)
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "MAX_FIRMWARE_SIZE", 10)
    code = main(["--backend", "socketcan", "--port", "can0", "--baud", "1000000", str(big)])
    assert code != 0
    assert "size" in capsys.readouterr().err.lower()


def test_main_errors_when_backend_fails_to_open(capsys, tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x00" * 8)
    import flasher.cli as cli_mod
    from flasher.backends.base import CanBackendError

    def raise_error(*args, **kwargs):
        raise CanBackendError("no such interface")

    monkeypatch.setattr(cli_mod, "SocketCanBackend", raise_error)
    code = main(["--backend", "socketcan", "--port", "not-real", "--baud", "1000000", str(fw)])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "interface" in err or "no such" in err


def test_main_returns_zero_on_a_full_successful_flash(tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01\x02\x03\x04\x05\x06\x07\x08")  # exactly one chunk

    fake_backend = FakeCanBackend(
        [
            CanFrame(RESP_READY_ACK, b""),  # enter bootloader
            CanFrame(RESP_READY_ACK, b""),  # chunk ack
            CanFrame(39, b""),  # socketcan app alive-ack
        ]
    )
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "SocketCanBackend", lambda channel, baud: fake_backend)

    code = main(["--backend", "socketcan", "--port", "can0", "--baud", "1000000", str(fw)])
    assert code == 0


def test_main_loads_backend_port_baud_from_config_file(tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)
    config_file = tmp_path / "flash.toml"
    config_file.write_text('backend = "socketcan"\nport = "can0"\nbaud = 1000000\n')

    fake_backend = FakeCanBackend(
        [
            CanFrame(RESP_READY_ACK, b""),
            CanFrame(RESP_READY_ACK, b""),
            CanFrame(39, b""),
        ]
    )
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "SocketCanBackend", lambda channel, baud: fake_backend)

    code = main(["--config", str(config_file), str(fw)])
    assert code == 0


def test_main_errors_when_flash_session_fails(capsys, tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)

    fake_backend = FakeCanBackend([])  # no responses at all: bootloader never ACKs
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "SocketCanBackend", lambda channel, baud: fake_backend)

    code = main(
        ["--backend", "socketcan", "--port", "can0", "--baud", "1000000", "--timeout-ms", "10", str(fw)]
    )
    assert code != 0
    assert "bootloader" in capsys.readouterr().err.lower()


def test_main_errors_when_backend_fails_mid_flash(capsys, tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)

    from flasher.backends.base import CanBackendError

    class RaisingBackend(FakeCanBackend):
        def send(self, can_id, data):
            if can_id != 0x02:  # let the enter-bootloader send succeed
                raise CanBackendError("bus off")
            return super().send(can_id, data)

    fake_backend = RaisingBackend([CanFrame(RESP_READY_ACK, b"")])
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "SocketCanBackend", lambda channel, baud: fake_backend)

    code = main(["--backend", "socketcan", "--port", "can0", "--baud", "1000000", str(fw)])
    assert code != 0
    assert "bus off" in capsys.readouterr().err.lower()


def test_main_errors_when_config_file_missing(capsys, tmp_path):
    missing_config = tmp_path / "nope.toml"
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)

    code = main(["--config", str(missing_config), str(fw)])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "config" in err


def test_main_errors_when_config_file_is_malformed_toml(capsys, tmp_path):
    bad_config = tmp_path / "flash.toml"
    bad_config.write_text("this is not valid toml {{{")
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)

    code = main(["--config", str(bad_config), str(fw)])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "config" in err


def test_main_errors_when_backend_value_is_invalid(capsys, tmp_path):
    config_file = tmp_path / "flash.toml"
    config_file.write_text('backend = "kvaser"\nport = "can0"\nbaud = 1000000\n')
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01" * 8)

    code = main(["--config", str(config_file), str(fw)])
    assert code != 0
    err = capsys.readouterr().err.lower()
    assert "backend" in err


def test_main_prints_success_message_on_a_full_successful_flash(capsys, tmp_path, monkeypatch):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x01\x02\x03\x04\x05\x06\x07\x08")

    fake_backend = FakeCanBackend(
        [
            CanFrame(RESP_READY_ACK, b""),
            CanFrame(RESP_READY_ACK, b""),
            CanFrame(39, b""),
        ]
    )
    import flasher.cli as cli_mod

    monkeypatch.setattr(cli_mod, "SocketCanBackend", lambda channel, baud: fake_backend)

    code = main(["--backend", "socketcan", "--port", "can0", "--baud", "1000000", str(fw)])
    assert code == 0
    out = capsys.readouterr().out.lower()
    assert "success" in out

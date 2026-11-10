import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


def _install_fake_canlib(monkeypatch):
    fake_canlib_inner = types.SimpleNamespace(
        canBITRATE_1M=object(),
        canBITRATE_500K=object(),
        canBITRATE_250K=object(),
        canBITRATE_125K=object(),
        canOPEN_EXCLUSIVE=object(),
        canError=Exception,
        canNoMsg=Exception,
        canMSG_ERROR_FRAME=Exception,
        openChannel=MagicMock(),
    )
    fake_canlib_pkg = types.ModuleType("canlib")
    fake_canlib_pkg.canlib = fake_canlib_inner
    monkeypatch.setitem(sys.modules, "canlib", fake_canlib_pkg)
    monkeypatch.setitem(sys.modules, "canlib.canlib", fake_canlib_inner)
    return fake_canlib_inner


def _reload_canlib_backend():
    import flasher.backends.canlib as canlib_backend_mod

    importlib.reload(canlib_backend_mod)
    return canlib_backend_mod


def test_resolve_bitrate_maps_known_baud_to_canlib_constant(monkeypatch):
    fake = _install_fake_canlib(monkeypatch)
    mod = _reload_canlib_backend()

    assert mod._resolve_bitrate(1000000) is fake.canBITRATE_1M
    assert mod._resolve_bitrate(500000) is fake.canBITRATE_500K


def test_resolve_bitrate_rejects_unknown_baud(monkeypatch):
    _install_fake_canlib(monkeypatch)
    mod = _reload_canlib_backend()
    from flasher.backends.base import CanBackendError

    with pytest.raises(CanBackendError):
        mod._resolve_bitrate(123456)


def test_init_uses_resolved_bitrate_not_raw_baud(monkeypatch):
    fake = _install_fake_canlib(monkeypatch)
    mod = _reload_canlib_backend()

    fake_channel = MagicMock()
    fake.openChannel = MagicMock(return_value=fake_channel)
    mod.CanlibBackend(channel=0, baud=1000000)
    fake_channel.setBusParams.assert_called_once_with(fake.canBITRATE_1M)

import pytest

from flasher.backends.base import CanBackend, CanFrame


def test_cannot_instantiate_abstract_backend():
    with pytest.raises(TypeError):
        CanBackend()


def test_can_frame_is_a_plain_data_holder():
    frame = CanFrame(can_id=0x7FE, data=b"\x00")
    assert frame.can_id == 0x7FE
    assert frame.data == b"\x00"

import abc
from dataclasses import dataclass


class CanBackendError(Exception):
    pass


@dataclass(frozen=True)
class CanFrame:
    can_id: int
    data: bytes


class CanBackend(abc.ABC):
    @abc.abstractmethod
    def send(self, can_id: int, data: bytes) -> bool:
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def recv(self, timeout_s: float) -> CanFrame | None:
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def shutdown(self) -> None:
        raise NotImplementedError  # pragma: no cover

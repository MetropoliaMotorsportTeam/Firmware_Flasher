from flasher.backends.base import CanBackend


class FakeCanBackend(CanBackend):
    """In-memory CanBackend for tests."""

    def __init__(self, responses, pending=None):
        self.responses = list(responses)  # normal recv() queue
        self.pending = list(pending) if pending else []  # drained only by a flush (timeout_s=0)
        self.sent = []
        self.calls = []  # ("send", can_id, data) | ("recv", timeout_s), in order

    def send(self, can_id, data):
        self.sent.append((can_id, data))
        self.calls.append(("send", can_id, data))
        return True

    def recv(self, timeout_s):
        self.calls.append(("recv", timeout_s))
        if timeout_s == 0:
            return self.pending.pop(0) if self.pending else None
        return self.responses.pop(0) if self.responses else None

    def shutdown(self):
        pass

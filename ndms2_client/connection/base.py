from typing import List

from ndms2_client.command import Command


class ResponseConverter:
    def convert(self, command, data):
        raise NotImplementedError("Should have implemented this")


class ConnectionException(Exception):
    pass


class Connection(object):
    @property
    def connected(self) -> bool:
        raise NotImplementedError("Should have implemented this")

    def connect(self):
        raise NotImplementedError("Should have implemented this")

    def disconnect(self):
        raise NotImplementedError("Should have implemented this")

    def run_command(self, command: Command, *, name: str = None) -> List[str]:
        raise NotImplementedError("Should have implemented this")

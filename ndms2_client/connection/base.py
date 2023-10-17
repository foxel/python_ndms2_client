from abc import ABC, abstractmethod
from typing import List
from ndms2_client.command import Command


class ResponseConverter(ABC):
    @abstractmethod
    def convert(self, command, data):
        ...


class ConnectionException(Exception):
    pass


class Connection(ABC):
    @property
    @abstractmethod
    def connected(self) -> bool:
        ...

    @abstractmethod
    def connect(self):
        ...

    @abstractmethod
    def disconnect(self):
        ...

    @abstractmethod
    def run_command(self, command: Command, *, name: str = None) -> List[str]:
        ...

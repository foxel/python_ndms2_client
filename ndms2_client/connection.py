import logging
import re
import telnetlib
from typing import List

_LOGGER = logging.getLogger(__name__)


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

    def run_command(self, command: str) -> List[str]:
        raise NotImplementedError("Should have implemented this")


class TelnetConnection(Connection):
    """Maintains a Telnet connection to a router."""

    @property
    def connected(self):
        return self._telnet is not None

    def __init__(self, host: str, port: int, username: str, password: str,
                 timeout: int = 30):
        """Initialize the Telnet connection properties."""
        self._telnet: telnetlib.Telnet = None
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._prompt_string: bytes = None

    def run_command(self, command):
        """Run a command through a Telnet connection.
         Connect to the Telnet server if not currently connected, otherwise
         use the existing connection.
        """
        if not self._telnet:
            self.connect()

        try:
            self._telnet.write('{}\n'.format(command).encode('ascii'))
            return self._read_until(self._prompt_string) \
                       .decode('ascii') \
                       .split('\n')[1:-1]
        except Exception as e:
            message = "Error executing command: %s" % str(e)
            _LOGGER.error(message)
            self.disconnect()
            raise ConnectionException(message) from None

    def connect(self):
        """Connect to the Telnet server."""
        try:
            self._telnet = telnetlib.Telnet(self._host, self._port,
                                            self._timeout)
            self._read_until(b'Login: ')
            self._telnet.write((self._username + '\n').encode('ascii'))
            self._read_until(b'Password: ')
            self._telnet.write((self._password + '\n').encode('ascii'))

            self._prompt_string = self._read_until(b'>').split(b'\n')[-1]
        except Exception:
            message = "Error connecting to telnet server"
            _LOGGER.error(message)
            self._telnet = None
            raise ConnectionException(message) from None

    def disconnect(self):
        """Disconnect the current Telnet connection."""
        try:
            if self._telnet:
                self._telnet.write(b'exit\n')
        except Exception as e:
            _LOGGER.error("Telnet error on exit: %s" % str(e))
            pass
        self._telnet = None

    def _read_until(self, needle: bytes):
        (i, _, text) = self._telnet.expect([re.escape(needle)], self._timeout)
        assert i is 0
        return text

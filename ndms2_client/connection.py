import logging
import re
from telnetlib import Telnet
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

    def __init__(self, host: str, port: int, username: str, password: str,
                 timeout: int = 30):
        """Initialize the Telnet connection properties."""
        self._telnet = None  # type: Telnet
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._prompt_string = None  # type: bytes

    @property
    def connected(self):
        return self._telnet is not None

    def run_command(self, command):
        """Run a command through a Telnet connection.
         Connect to the Telnet server if not currently connected, otherwise
         use the existing connection.
        """
        if not self._telnet:
            self.connect()

        try:
            self._telnet.read_very_eager()  # this is here to flush the read buffer
            self._telnet.write('{}\n'.format(command).encode('UTF-8'))
            return self._read_until(self._prompt_string) \
                       .decode('UTF-8') \
                       .split('\n')[1:-1]
        except Exception as e:
            message = "Error executing command: %s" % str(e)
            _LOGGER.error(message)
            self.disconnect()
            raise ConnectionException(message) from None

    def connect(self):
        """Connect to the Telnet server."""
        try:
            self._telnet = Telnet(self._host, self._port, self._timeout)
            self._telnet.set_option_negotiation_callback(TelnetConnection.__set_max_window_size)

            self._read_until(b'Login: ')
            self._telnet.write((self._username + '\n').encode('UTF-8'))
            self._read_until(b'Password: ')
            self._telnet.write((self._password + '\n').encode('UTF-8'))

            self._prompt_string = self._read_until(b'>').split(b'\n')[-1]
        except Exception as e:
            message = "Error connecting to telnet server: %s" % str(e)
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
        assert i is 0, "No expected response from server"
        return text

    # noinspection PyProtectedMember
    @staticmethod
    def __set_max_window_size(tsocket, command, option):
        """
        Set Window size to resolve line width issue
        Set Windows size command: IAC SB NAWS <16-bit value> <16-bit value> IAC SE
        --> inform the Telnet server of the window width and height.
        Refer to https://www.ietf.org/rfc/rfc1073.txt
        :param tsocket: telnet socket object
        :param command: telnet Command
        :param option: telnet option
        :return: None
        """
        from telnetlib import DO, DONT, IAC, WILL, WONT, NAWS, SB, SE
        import struct

        if option == NAWS:
            width = struct.pack('H', 65000)
            height = struct.pack('H', 5000)
            tsocket.send(IAC + WILL + NAWS)
            tsocket.send(IAC + SB + NAWS + width + height + IAC + SE)
        # -- below code taken from telnetlib source
        elif command in (DO, DONT):
            tsocket.send(IAC + WONT + option)
        elif command in (WILL, WONT):
            tsocket.send(IAC + DONT + option)


import logging
import re
from telnetlib import Telnet
from typing import List, Union, Pattern, Match, Dict, Optional
from .command import Command

_LOGGER = logging.getLogger(__name__)

_ARP_REGEX = re.compile(
    r'(?P<name>.*?)\s+' +
    r'(?P<ip>([0-9]{1,3}[.]){3}[0-9]{1,3})?\s+' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))\s+' +
    r'(?P<interface>([^ ]+))\s+'
)


class ResponseConverter:
    def convert(self, command, data):
        raise NotImplementedError("Should have implemented this")


class TelnetResponseConverter(ResponseConverter):
    def convert(self, command, data):
        if command in (
            Command.VERSION,
            Command.INTERFACE,
            Command.ASSOCIATIONS,
            Command.HOTSPOT,
        ):
            return self._parse_dict_lines(data)
        elif command == Command.INTERFACES:
            return self._parse_collection_lines(data)
        elif command == Command.ARP:
            return self._parse_table_lines(data)

        return data

    def _parse_table_lines(self, lines: List[str]) -> List[Dict[str, any]]:
        """Parse the lines using the given regular expression.
         If a line can't be parsed it is logged and skipped in the output.
        """
        results = []
        for line in lines:
            match = _ARP_REGEX.search(line)
            if not match:
                _LOGGER.debug('Could not parse line: %s', line)
                continue
            results.append(match.groupdict())
        return results

    def _fix_continuation_lines(self, lines: List[str]) -> List[str]:
        indent = 0
        continuation_possible = False
        fixed_lines = []  # type: List[str]
        for line in lines:
            if len(line.strip()) == 0:
                continue

            if continuation_possible and len(line[:indent].strip()) == 0:
                prev_line = fixed_lines.pop()
                line = prev_line.rstrip() + line[(indent + 1):].lstrip()
            else:
                assert ':' in line, 'Found a line with no colon when continuation is not possible: ' + line

                colon_pos = line.index(':')
                comma_pos = line.index(',') if ',' in line[:colon_pos] else None
                indent = comma_pos if comma_pos is not None else colon_pos

                continuation_possible = len(line[(indent + 1):].strip()) > 0

            fixed_lines.append(line)

        return fixed_lines

    def _parse_dict_lines(self, lines: List[str]) -> Dict[str, any]:
        response = {}
        indent = 0
        stack = [(None, indent, response)]  # type: List[Tuple[str, int, Union[str, dict]]]
        stack_level = 0

        for line in self._fix_continuation_lines(lines):
            if len(line.strip()) == 0:
                continue

            _LOGGER.debug(line)

            # exploding the line
            colon_pos = line.index(':')
            comma_pos = line.index(',') if ',' in line[:colon_pos] else None
            key = line[:colon_pos].strip()
            value = line[(colon_pos + 1):].strip()
            new_indent = comma_pos if comma_pos is not None else colon_pos

            # assuming line is like 'mac-access, id = Bridge0: ...'
            if comma_pos is not None:
                key = line[:comma_pos].strip()

                value = {key: value} if value != '' else {}

                args = line[comma_pos + 1:colon_pos].split(',')
                for arg in args:
                    sub_key, sub_value = [p.strip() for p in arg.split('=', 1)]
                    value[sub_key] = sub_value

            # up and down the stack
            if new_indent > indent:  # new line is a sub-value of parent
                stack_level += 1
                indent = new_indent
                stack.append(None)
            else:
                while new_indent < indent and len(stack) > 0:  # getting one level up
                    stack_level -= 1
                    stack.pop()
                    _, indent, _ = stack[stack_level]

            if stack_level < 1:
                break

            assert indent == new_indent, 'Irregular indentation detected'

            stack[stack_level] = key, indent, value

            # current containing object
            obj_key, obj_indent, obj = stack[stack_level - 1]

            # we are the first child of the containing object
            if not isinstance(obj, dict):
                # need to convert it from empty string to empty object
                assert obj == '', 'Unexpected nested object format'
                _, _, parent_obj = stack[stack_level - 2]
                obj = {}

                # containing object might be in a list also
                if isinstance(parent_obj[obj_key], list):
                    parent_obj[obj_key].pop()
                    parent_obj[obj_key].append(obj)
                else:
                    parent_obj[obj_key] = obj
                stack[stack_level - 1] = obj_key, obj_indent, obj

            # current key is already in object means there should be an array of values
            if key in obj:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]

                obj[key].append(value)
            else:
                obj[key] = value

        return response

    def _parse_collection_lines(self, lines: List[str]) -> List[Dict[str, any]]:
        _HEADER_REGEXP = re.compile(r'^(\w+),\s*name\s*=\s*\"([^"]+)\"')

        result = []
        item_lines = []  # type: List[str]
        for line in lines:
            if len(line.strip()) == 0:
                continue

            match = _HEADER_REGEXP.match(line)
            if match:
                if len(item_lines) > 0:
                    result.append(self._parse_dict_lines(item_lines))
                    item_lines = []
            else:
                item_lines.append(line)

        if len(item_lines) > 0:
            result.append(self._parse_dict_lines(item_lines))

        return result


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


class TelnetConnection(Connection):
    """Maintains a Telnet connection to a router."""

    def __init__(self, host: str, port: int, username: str, password: str, *,
                 timeout: int = 30, response_converter: Optional[ResponseConverter] = None):
        """Initialize the Telnet connection properties."""
        self._telnet = None  # type: Telnet
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._current_prompt_string = None  # type: bytes
        self._converter = response_converter

    @property
    def connected(self):
        return self._telnet is not None

    def run_command(self, command: Command, *, name=None, group_change_expected=False) -> List[str]:
        """Run a command through a Telnet connection.
         Connect to the Telnet server if not currently connected, otherwise
         use the existing connection.
        """
        cmd = command.value
        if name:
            cmd = command.value % name
        if not self._telnet:
            self.connect()

        try:
            self._telnet.read_very_eager()  # this is here to flush the read buffer
            self._telnet.write('{}\n'.format(cmd).encode('UTF-8'))
            response = self._read_response(group_change_expected)
        except Exception as e:
            message = "Error executing command: %s" % str(e)
            _LOGGER.error(message)
            self.disconnect()
            raise ConnectionException(message) from None
        else:
            _LOGGER.debug('Command %s: %s', cmd, '\n'.join(response))
            if self._converter:
                return self._converter.convert(command, response)
            return response

    def connect(self):
        """Connect to the Telnet server."""
        try:
            self._telnet = Telnet()
            self._telnet.set_option_negotiation_callback(TelnetConnection.__negotiate_naws)
            self._telnet.open(self._host, self._port, self._timeout)

            self._read_until(b'Login: ')
            self._telnet.write((self._username + '\n').encode('UTF-8'))
            self._read_until(b'Password: ')
            self._telnet.write((self._password + '\n').encode('UTF-8'))

            self._read_response(True)
            self._set_max_window_size()
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

    def _read_response(self, detect_new_prompt_string=False) -> List[str]:
        needle = re.compile(br'\n\(\w+[-\w]+\)>') if detect_new_prompt_string else self._current_prompt_string
        (match, text) = self._read_until(needle)
        if detect_new_prompt_string:
            self._current_prompt_string = match[0]
        return text.decode('UTF-8').split('\n')[1:-1]

    def _read_until(self, needle: Union[bytes, Pattern]) -> (Match, bytes):
        matcher = needle if isinstance(needle, Pattern) else re.escape(needle)
        (i, match, text) = self._telnet.expect([matcher], self._timeout)
        assert i == 0, "No expected response from server"
        return match, text

    # noinspection PyProtectedMember
    def _set_max_window_size(self):
        """
        --> inform the Telnet server of the window width and height. see __negotiate_naws
        """
        from telnetlib import IAC, NAWS, SB, SE
        import struct

        width = struct.pack('H', 65000)
        height = struct.pack('H', 5000)
        self._telnet.get_socket().sendall(IAC + SB + NAWS + width + height + IAC + SE)

    # noinspection PyProtectedMember
    @staticmethod
    def __negotiate_naws(tsocket, command, option):
        """
        --> inform the Telnet server we'll be using Window Size Option.
        Refer to https://www.ietf.org/rfc/rfc1073.txt
        :param tsocket: telnet socket object
        :param command: telnet Command
        :param option: telnet option
        :return: None
        """
        from telnetlib import DO, DONT, IAC, WILL, WONT, NAWS

        if option == NAWS:
            tsocket.sendall(IAC + WILL + NAWS)
        # -- below code taken from telnetlib
        elif command in (DO, DONT):
            tsocket.sendall(IAC + WONT + option)
        elif command in (WILL, WONT):
            tsocket.sendall(IAC + DONT + option)

import logging
import re
from collections import namedtuple
from typing import Dict, List, Optional

from .connection import Connection

_LOGGER = logging.getLogger(__name__)


_ARP_CMD = 'show ip arp'
_ARP_REGEX = re.compile(
    r'(?P<name>([^ ]+))\s+' +
    r'(?P<ip>([0-9]{1,3}[.]){3}[0-9]{1,3})\s+' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))\s+' +
    r'(?P<interface>([^ ]+))\s+'
)

Device = namedtuple('Device', ['mac', 'name', 'ip', 'interface'])


class Client(object):
    def __init__(self, connection: Connection):
        self._connection = connection

    def get_devices(self) -> List[Device]:
        lines = self._connection.run_command(_ARP_CMD)

        result = _parse_lines(lines, _ARP_REGEX)

        return [Device(
            info.get('mac').upper(),
            info.get('name'),
            info.get('ip'),
            info.get('interface')
        ) for info in result if info.get('mac') is not None]


def _parse_lines(lines: List[str], regex: re) -> List[Dict[str, any]]:
    """Parse the lines using the given regular expression.
     If a line can't be parsed it is logged and skipped in the output.
    """
    results = []
    for line in lines:
        match = regex.search(line)
        if not match:
            _LOGGER.debug("Could not parse line: %s", line)
            continue
        results.append(match.groupdict())
    return results

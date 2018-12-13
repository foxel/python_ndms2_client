import logging
import re
from collections import namedtuple
from typing import Dict, List

from .connection import Connection

_LOGGER = logging.getLogger(__name__)


_ARP_CMD = 'show ip arp'
_ASSOCIATIONS_CMD = 'show associations'
_HOTSPOT_CMD = 'show ip hotspot'
_INTERFACE_CMD = 'show interface %s'
_ARP_REGEX = re.compile(
    r'(?P<name>([^ ]+))?\s+' +
    r'(?P<ip>([0-9]{1,3}[.]){3}[0-9]{1,3})?\s+' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))\s+' +
    r'(?P<interface>([^ ]+))\s+'
)

Device = namedtuple('Device', ['mac', 'name', 'ip', 'interface'])


class Client(object):
    def __init__(self, connection: Connection):
        self._connection = connection

    def get_devices(self, include_arp=True, include_associated=True) -> List[Device]:
        devices = []

        if include_arp:
            devices = _merge_devices(devices, self.get_arp_devices())

        if include_associated:
            devices = _merge_devices(devices, self.get_associated_devices())

        return devices

    def get_arp_devices(self) -> List[Device]:
        lines = self._connection.run_command(_ARP_CMD)

        result = _parse_table_lines(lines, _ARP_REGEX)

        return [Device(
            mac=info.get('mac').upper(),
            name=info.get('name'),
            ip=info.get('ip'),
            interface=info.get('interface')
        ) for info in result if info.get('mac') is not None]

    def get_associated_devices(self):
        associations = _parse_dict_lines(self._connection.run_command(_ASSOCIATIONS_CMD))

        items = associations.get('station', [])
        if not isinstance(items, list):
            items = [items]

        aps = set([info.get('ap') for info in items])

        ap_to_bridge = {}
        for ap in aps:
            ap_info = _parse_dict_lines(self._connection.run_command(_INTERFACE_CMD % ap))
            ap_to_bridge[ap] = ap_info.get('group') or ap_info.get('interface-name')

        hotspot_info = self.__get_hotpot_info()

        devices = []

        for info in items:
            mac = info.get('mac')
            if mac is not None and info.get('authenticated') in ['1', 'yes']:
                host_info = hotspot_info.get(mac)

                devices.append(Device(
                    mac=mac.upper(),
                    name=host_info.get('name') if host_info else None,
                    ip=host_info.get('ip') if host_info else None,
                    interface=ap_to_bridge.get(info.get('ap'), info.get('ap'))
                ))

        return devices

    # hotspot info is only available in newest firmware
    # however on older firmware missing command error will lead to empty dict returned
    def __get_hotpot_info(self):
        info = _parse_dict_lines(self._connection.run_command(_HOTSPOT_CMD))

        items = info.get('host', [])
        if not isinstance(items, list):
            items = [items]

        return {item.get('mac'): item for item in items}


def _merge_devices(left: List[Device], right: List[Device]) -> List[Device]:
    existing_macs = set([d.mac for d in left])
    return left + [d for d in right if d.mac not in existing_macs]


def _parse_table_lines(lines: List[str], regex: re) -> List[Dict[str, any]]:
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


def _parse_dict_lines(lines: List[str]) -> Dict[str, any]:
    response = {}
    stack = [(None, response)]
    stack_level = 0
    indent = 0

    # fixing line feeds in response
    fixed_lines = []
    for line in lines:
        if len(line.strip()) == 0:
            continue

        if ':' not in line:
            assert len(fixed_lines) > 0, "Found a line with no colon in the beginning of the file"
            prev_line = fixed_lines.pop()
            line = prev_line + ' ' + line.strip()

        fixed_lines.append(line)

    for line in fixed_lines:
        # exploding the line
        colon_pos = line.index(':')
        comma_pos = line.index(',') if ',' in line else None
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
            stack.append(None)
        elif new_indent < indent:  # getting one level up
            stack_level -= 1
            stack.pop()

        if stack_level < 1:
            break

        indent = new_indent
        stack[stack_level] = key, value

        # current containing object
        obj_key, obj = stack[stack_level - 1]

        # we are the first child of the containing object
        if not isinstance(obj, dict):
            # need to convert it from empty string to empty object
            assert obj == ''
            _, parent_obj = stack[stack_level - 2]
            obj = {}

            # containing object might be in a list also
            if isinstance(parent_obj[obj_key], list):
                parent_obj[obj_key].pop()
                parent_obj[obj_key].append(obj)
            else:
                parent_obj[obj_key] = obj
            stack[stack_level - 1] = obj_key, obj

        # current key is already in object means there should be an array of values
        if key in obj:
            if not isinstance(obj[key], list):
                obj[key] = [obj[key]]

            obj[key].append(value)
        else:
            obj[key] = value

    return response

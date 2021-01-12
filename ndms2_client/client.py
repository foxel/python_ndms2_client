import logging
import re
from collections import namedtuple
from typing import Dict, List, Tuple, Union

from .connection import Connection

_LOGGER = logging.getLogger(__name__)


_VERSION_CMD = 'show version'
_ARP_CMD = 'show ip arp'
_ASSOCIATIONS_CMD = 'show associations'
_HOTSPOT_CMD = 'show ip hotspot'
_INTERFACE_CMD = 'show interface %s'
_ARP_REGEX = re.compile(
    r'(?P<name>.*?)\s+' +
    r'(?P<ip>([0-9]{1,3}[.]){3}[0-9]{1,3})?\s+' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))\s+' +
    r'(?P<interface>([^ ]+))\s+'
)

Device = namedtuple('Device', ['mac', 'name', 'ip', 'interface'])
RouterInfo = namedtuple('RouterInfo', [
    'name',
    'fw_version',
    'fw_channel',
    'model',
    'hw_version',
    'manufacturer',
    'vendor',
    'region',
])


class Client(object):
    def __init__(self, connection: Connection):
        self._connection = connection

    def get_router_info(self):
        info = _parse_dict_lines(self._connection.run_command(_VERSION_CMD))

        if not isinstance(info, dict):
            return None

        return RouterInfo(
            name=str(info.get('description', info.get('model', 'NDMS2 Router'))),
            fw_version=str(info.get('title', info.get('release'))),
            fw_channel=str(info.get('sandbox', 'unknown')),
            model=str(info.get('model', info.get('hw_id'))),
            hw_version=str(info.get('hw_version', 'N/A')),
            manufacturer=str(info.get('manufacturer')),
            vendor=str(info.get('vendor')),
            region=str(info.get('region', 'N/A')),
        )

    def get_devices(self, *, try_hotspot=True, include_arp=True, include_associated=True) -> List[Device]:
        """
            Fetches a list of connected devices online
            :param try_hotspot: first try `ip hotspot` command.
            This is the most precise information on devices known to be online
            :param include_arp: if try_hotspot is False or no hotspot devices detected
            :param include_associated:
            :return:
        """
        devices = []

        if try_hotspot:
            devices = _merge_devices(devices, self.get_hotspot_devices())
            if len(devices) > 0:
                return devices

        if include_arp:
            devices = _merge_devices(devices, self.get_arp_devices())

        if include_associated:
            devices = _merge_devices(devices, self.get_associated_devices())

        return devices

    def get_hotspot_devices(self) -> List[Device]:
        hotspot_info = self.__get_hotspot_info()

        return [Device(
            mac=info.get('mac').upper(),
            name=info.get('name'),
            ip=info.get('ip'),
            interface=info['interface'].get('name', '')
        ) for info in hotspot_info.values() if 'interface' in info and info.get('link') == 'up']

    def get_arp_devices(self) -> List[Device]:
        lines = self._connection.run_command(_ARP_CMD)

        result = _parse_table_lines(lines, _ARP_REGEX)

        return [Device(
            mac=info.get('mac').upper(),
            name=info.get('name') or None,
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

        # try enriching the results with hotspot additional info
        hotspot_info = self.__get_hotspot_info()

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

    # hotspot info is only available in newest firmware (2.09 and up) and in router mode
    # however missing command error will lead to empty dict returned
    def __get_hotspot_info(self):
        info = _parse_dict_lines(self._connection.run_command(_HOTSPOT_CMD))

        items = info.get('host', [])
        if not isinstance(items, list):
            items = [items]

        return {item.get('mac'): item for item in items}


def _merge_devices(*lists: List[Device]) -> List[Device]:
    res = {}
    for l in lists:
        for dev in l:
            key = (dev.interface, dev.mac)
            if key in res:
                old_dev = res.get(key)
                res[key] = Device(
                    mac=old_dev.mac,
                    name=old_dev.name or dev.name,
                    ip=old_dev.ip or dev.ip,
                    interface=old_dev.interface
                )
            else:
                res[key] = dev

    return list(res.values())


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


def _fix_continuation_lines(lines: List[str]) -> List[str]:
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


def _parse_dict_lines(lines: List[str]) -> Dict[str, any]:
    response = {}
    indent = 0
    stack = [(None, indent, response)]  # type: List[Tuple[str, int, Union[str, dict]]]
    stack_level = 0

    for line in _fix_continuation_lines(lines):
        if len(line.strip()) == 0:
            continue

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

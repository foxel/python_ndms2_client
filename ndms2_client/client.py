import logging
import re
from typing import Dict, List, Tuple, Union, NamedTuple, Optional

from .connection import Connection
from .command import Command

_LOGGER = logging.getLogger(__name__)


class Device(NamedTuple):
    mac: str
    name: str
    ip: str
    interface: str

    @staticmethod
    def merge_devices(*lists: List["Device"]) -> List["Device"]:
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


class RouterInfo(NamedTuple):
    name: str
    fw_version: str
    fw_channel: str
    model: str
    hw_version: str
    manufacturer: str
    vendor: str
    region: str
    
    @classmethod
    def from_dict(cls, info: dict) -> "RouterInfo":
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


class InterfaceInfo(NamedTuple):
    name: str
    type: Optional[str]
    description: Optional[str]
    link: Optional[str]
    connected: Optional[str]
    state: Optional[str]
    mtu: Optional[int]
    address: Optional[str]
    mask: Optional[str]
    uptime: Optional[int]
    security_level: Optional[str]
    mac: Optional[str]

    @classmethod
    def from_dict(cls, info: dict) -> "InterfaceInfo":
        return InterfaceInfo(
            name=_str(info.get('interface-name')) or str(info['id']),
            type=_str(info.get('type')),
            description=_str(info.get('description')),
            link=_str(info.get('link')),
            connected=_str(info.get('connected')),
            state=_str(info.get('state')),
            mtu=_int(info.get('mtu')),
            address=_str(info.get('address')),
            mask=_str(info.get('mask')),
            uptime=_int(info.get('uptime')),
            security_level=_str(info.get('security-level')),
            mac=_str(info.get('mac')),
        )


class Client(object):
    def __init__(self, connection: Connection):
        self._connection = connection

    def get_router_info(self) -> RouterInfo:
        info = self._connection.run_command(Command.VERSION)

        _LOGGER.debug('Raw router info: %s', str(info))
        assert isinstance(info, dict), 'Router info response is not a dictionary'
        
        return RouterInfo.from_dict(info)

    def get_interfaces(self) -> List[InterfaceInfo]:
        collection = self._connection.run_command(Command.INTERFACES)

        _LOGGER.debug('Raw interfaces info: %s', str(collection))
        assert isinstance(collection, list), 'Interfaces info response is not a collection'

        return [InterfaceInfo.from_dict(info) for info in collection]

    def get_interface_info(self, interface_name) -> Optional[InterfaceInfo]:
        info = self._connection.run_command(Command.INTERFACE, name=interface_name)

        _LOGGER.debug('Raw interface info: %s', str(info))
        assert isinstance(info, dict), 'Interface info response is not a dictionary'

        if 'id' in info:
            return InterfaceInfo.from_dict(info)

        return None

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
            devices = Device.merge_devices(devices, self.get_hotspot_devices())
            if len(devices) > 0:
                return devices

        if include_arp:
            devices = Device.merge_devices(devices, self.get_arp_devices())

        if include_associated:
            devices = Device.merge_devices(devices, self.get_associated_devices())

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
        result = self._connection.run_command(Command.ARP)

        return [Device(
            mac=info.get('mac').upper(),
            name=info.get('name') or None,
            ip=info.get('ip'),
            interface=info.get('interface')
        ) for info in result if info.get('mac') is not None]

    def get_associated_devices(self):
        associations = self._connection.run_command(Command.ASSOCIATIONS)

        items = associations.get('station', [])
        if not isinstance(items, list):
            items = [items]

        aps = set([info.get('ap') for info in items])

        ap_to_bridge = {}
        for ap in aps:
            ap_info = self._connection.run_command(Command.INTERFACE, name=ap)
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
        info = self._connection.run_command(Command.HOTSPOT)

        items = info.get('host', [])
        if not isinstance(items, list):
            items = [items]

        return {item.get('mac'): item for item in items}


def _str(value: Optional[any]) -> Optional[str]:
    if value is None:
        return None

    return str(value)


def _int(value: Optional[any]) -> Optional[int]:
    if value is None:
        return None

    return int(value)

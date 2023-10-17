import logging
from typing import List, Optional

from .command import Command
from .connection import Connection
from .models import Device, InterfaceInfo, RouterInfo

_LOGGER = logging.getLogger(__name__)


class Client(object):
    def __init__(self, connection: Connection):
        self._connection = connection

    def get_router_info(self) -> RouterInfo:
        info = self._connection.run_command(Command.VERSION)

        _LOGGER.debug("Raw router info: %s", str(info))
        assert isinstance(info, dict), "Router info response is not a dictionary"

        return RouterInfo.from_dict(info)

    def get_interfaces(self) -> List[InterfaceInfo]:
        collection = self._connection.run_command(Command.INTERFACES)

        _LOGGER.debug("Raw interfaces info: %s", str(collection))
        assert isinstance(collection, list), "Interfaces info response is not a collection"

        return [InterfaceInfo.from_dict(info) for info in collection]

    def get_interface_info(self, interface_name) -> Optional[InterfaceInfo]:
        info = self._connection.run_command(Command.INTERFACE, name=interface_name)

        _LOGGER.debug("Raw interface info: %s", str(info))
        assert isinstance(info, dict), "Interface info response is not a dictionary"

        if "id" in info:
            return InterfaceInfo.from_dict(info)

        return None

    def get_devices(
        self,
        *,
        try_hotspot=True,
        include_arp=True,
        include_associated=True,
    ) -> List[Device]:
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

        return [
            Device(
                mac=info.get("mac").upper(),
                name=info.get("name"),
                ip=info.get("ip"),
                interface=info["interface"].get("name", ""),
            )
            for info in hotspot_info.values()
            if "interface" in info and info.get("link") == "up"
        ]

    def get_arp_devices(self) -> List[Device]:
        result = self._connection.run_command(Command.ARP)

        return [
            Device(
                mac=info.get("mac").upper(),
                name=info.get("name") or None,
                ip=info.get("ip"),
                interface=info.get("interface"),
            )
            for info in result
            if info.get("mac") is not None
        ]

    def get_associated_devices(self):
        associations = self._connection.run_command(Command.ASSOCIATIONS)

        items = associations.get("station", [])
        if not isinstance(items, list):
            items = [items]

        aps = set([info.get("ap") for info in items])

        ap_to_bridge = {}
        for ap in aps:
            ap_info = self._connection.run_command(Command.INTERFACE, name=ap)
            ap_to_bridge[ap] = ap_info.get("group") or ap_info.get("interface-name")

        # try enriching the results with hotspot additional info
        hotspot_info = self.__get_hotspot_info()

        devices = []

        for info in items:
            mac = info.get("mac")
            if mac is not None and info.get("authenticated") in ["1", "yes", True]:
                host_info = hotspot_info.get(mac)

                devices.append(
                    Device(
                        mac=mac.upper(),
                        name=host_info.get("name") if host_info else None,
                        ip=host_info.get("ip") if host_info else None,
                        interface=ap_to_bridge.get(info.get("ap"), info.get("ap")),
                    ),
                )

        return devices

    # hotspot info is only available in newest firmware (2.09 and up) and in router mode
    # however missing command error will lead to empty dict returned
    def __get_hotspot_info(self):
        info = self._connection.run_command(Command.HOTSPOT)

        items = info.get("host", [])
        if not isinstance(items, list):
            items = [items]

        return {item.get("mac"): item for item in items}

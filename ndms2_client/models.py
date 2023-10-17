from typing import List, NamedTuple, Optional


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
                        interface=old_dev.interface,
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
            name=str(info.get("description", info.get("model", "NDMS2 Router"))),
            fw_version=str(info.get("title", info.get("release"))),
            fw_channel=str(info.get("sandbox", "unknown")),
            model=str(info.get("model", info.get("hw_id"))),
            hw_version=str(info.get("hw_version", "N/A")),
            manufacturer=str(info.get("manufacturer")),
            vendor=str(info.get("vendor")),
            region=str(info.get("region", "N/A")),
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
            name=_str(info.get("interface-name")) or str(info["id"]),
            type=_str(info.get("type")),
            description=_str(info.get("description")),
            link=_str(info.get("link")),
            connected=_str(info.get("connected")),
            state=_str(info.get("state")),
            mtu=_int(info.get("mtu")),
            address=_str(info.get("address")),
            mask=_str(info.get("mask")),
            uptime=_int(info.get("uptime")),
            security_level=_str(info.get("security-level")),
            mac=_str(info.get("mac")),
        )


def _str(value: Optional[any]) -> Optional[str]:
    if value is None:
        return None

    return str(value)


def _int(value: Optional[any]) -> Optional[int]:
    if value is None:
        return None

    return int(value)

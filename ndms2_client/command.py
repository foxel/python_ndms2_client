from enum import Enum


class Command(Enum):
    VERSION = 'show version'
    ARP = 'show ip arp'
    ASSOCIATIONS = 'show associations'
    HOTSPOT = 'show ip hotspot'
    INTERFACE = 'show interface %s'
    INTERFACES = 'show interface'

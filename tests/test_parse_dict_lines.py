import os
import sys
from typing import Tuple

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# noinspection PyProtectedMember
def test_parse_dict_lines(dict_text):
    from ndms2_client.client import _parse_dict_lines

    _parse_dict_lines(dict_text.split('\n'))


def test_hotspot_data(hostpot_sample: Tuple[str, int]):
    from ndms2_client.client import _parse_dict_lines

    sample, expected_hosts = hostpot_sample

    parsed = _parse_dict_lines(sample.split('\n'))

    print(parsed['host'])

    if expected_hosts > 1:
        assert isinstance(parsed['host'], list)
        assert len(parsed['host']) == expected_hosts
    else:
        assert isinstance(parsed['host'], dict)


@pytest.fixture(params=range(4))
def dict_text(request):
    data = ['''

          station: 
                  mac: 60:ff:ff:ff:ff:ff
                   ap: WifiMaster0/AccessPoint0
        authenticated: yes
               txrate: 65
               rxrate: 54
               uptime: 3558
              txbytes: 56977
              rxbytes: 21754
                   ht: 20
                 mode: 11n
                   gi: 800
                 rssi: -46
                  mcs: 7
                 txss: 1

          station: 
                  mac: b8:ff:ff:ff:ff:ff
                   ap: WifiMaster0/AccessPoint0
        authenticated: yes
               txrate: 65
               rxrate: 24
               uptime: 3557
              txbytes: 9261871
              rxbytes: 196082452
                   ht: 20
                 mode: 11n
                   gi: 800
                 rssi: -54
                  mcs: 7
                 txss: 1

          station: 
                  mac: 5c:ff:ff:ff:ff:ff
                   ap: WifiMaster0/AccessPoint0
        authenticated: yes
               txrate: 65
               rxrate: 36
               uptime: 3555
              txbytes: 74073
              rxbytes: 21007
                   ht: 20
                 mode: 11n
                   gi: 800
                 rssi: -54
                  mcs: 7
                 txss: 1

          station: 
                  mac: 60:ff:ff:ff:ff:ff
                   ap: WifiMaster0/AccessPoint0
        authenticated: yes
               txrate: 65
               rxrate: 6
               uptime: 3554
              txbytes: 92221
              rxbytes: 21475
                   ht: 20
                 mode: 11n
                   gi: 800
                 rssi: -63
                  mcs: 7
                 txss: 1

          station: 
                  mac: 48:ff:ff:ff:ff:ff
                   ap: WifiMaster0/AccessPoint0
        authenticated: yes
               txrate: 65
               rxrate: 65
               uptime: 3423
              txbytes: 697534
              rxbytes: 732250
                   ht: 20
                 mode: 11n
                   gi: 800
                 rssi: -20
                  mcs: 7
                 txss: 1

          station: 
                  mac: a4:ff:ff:ff:ff:ff
                   ap: WifiMaster1/AccessPoint0
        authenticated: yes
               txrate: 200
               rxrate: 200
               uptime: 1749
              txbytes: 1012970
              rxbytes: 1183758
                   ht: 40
                 mode: 11ac
                   gi: 400
                 rssi: -63
                  mcs: 9
                 txss: 1

          station: 
                  mac: a4:ff:ff:ff:ff:ff
                   ap: WifiMaster1/AccessPoint0
        authenticated: yes
               txrate: 200
               rxrate: 180
               uptime: 1741
              txbytes: 586118
              rxbytes: 658847
                   ht: 40
                 mode: 11ac
                   gi: 400
                 rssi: -71
                  mcs: 9
                 txss: 1

''', '''

          buttons: 
               button, name = RESET: 
                is_switch: no
                 position: 2
           position_count: 2
                   clicks: 0
                  elapsed: 0
               hold_delay: 10000

               button, name = WLAN: 
                is_switch: no
                 position: 2
           position_count: 2
                   clicks: 0
                  elapsed: 0
               hold_delay: 3000

               button, name = FN1: 
                is_switch: no
                 position: 2
           position_count: 2
                   clicks: 0
                  elapsed: 0
               hold_delay: 3000

               button, name = FN2: 
                is_switch: no
                 position: 2
           position_count: 2
                   clicks: 0
                  elapsed: 0
               hold_delay: 3000


''', '''

               id: WifiMaster0/AccessPoint0
            index: 0
             type: AccessPoint
      description: Wi-Fi access point
   interface-name: AccessPoint
             link: up
        connected: yes
            state: up
              mtu: 1500
         tx-queue: 1000
            group: Home

           usedby: Bridge0

              mac: 00:ff:00:00:00:00
        auth-type: none
             ssid: home
       encryption: wpa2,wpa3

''', '''

          release: v2.08(AAUR.4)C2
             arch: mips
              ndm: 
                exact: 0-df82a04
                cdate: 16 Oct 2017
              bsp: 
                exact: 0-02ec1b2
                cdate: 16 Oct 2017
              ndw: 
              version: 4.2.0.166
             features: wifi_button,single_usb_port,nopack,
                       flexible_menu,emulate_firmware_progress
           components: ddns,dot1x,interface-extras,kabinet,
                       miniupnpd,nathelper-ftp,nathelper-h323,nathelper-pptp,
                       nathelper-rtsp,nathelper-sip,ppe,trafficcontrol,usblte,
                       usbserial,base,cloud,cloudcontrol,components,config-ap,
                       config-client,config-repeater,corewireless,dhcpd,
                       easyconfig,igmp,ipsec,l2tp,madwimax,pingcheck,ppp,pptp,
                       pppoe,skydns,usb,usbdsl,usbmodem,usbnet,ydns,vpnserver,
                       base-l10n,sysmode,easyconfig-3.2,modems,theme-ZyXEL-Intl,
                       base-theme,ispdb,base-ZyXEL-Intl
     manufacturer: ZyXEL
           vendor: ZyXEL
           series: Keenetic series
            model: Keenetic
       hw_version: 12131000-G
            hw_id: kn_rg
           device: Keenetic 4G III
            class: Internet Center

''']
    return data[request.param]


@pytest.fixture(params=range(2))
def hostpot_sample(request) -> Tuple[str, int]:
    samples = [
        ('''
        
             host:
                  mac: dc:09:xx:xx:xx:xx
                  via: dc:09:xx:xx:xx:xx
                   ip: 192.xx.xx.xx
             hostname: xxxxxxxxxxxxx
                 name: xxxxxxxxxxxxxxxxxx

            interface:
                       id: Bridge0
                     name: Home
              description: Home VLAN

              expires: 181613
           registered: yes
               access: permit
             schedule:
               active: yes
              rxbytes: 34442317
              txbytes: 2176340
               uptime: 59
           first-seen: 157428
            last-seen: 7
                 link: up
     auto-negotiation: yes
                speed: 1000
               duplex: yes
            ever-seen: yes

        traffic-shape:
                       rx: 0
                       tx: 0
                     mode: mac
                 schedule:

             host:
                  mac: 10:40:xx:xx:xx:xx
                  via: 10:40:xx:xx:xx:xx
                   ip: 192.xx.xx.xx
             hostname: xxxxxxxxxxxxx
                 name: xxxxxxxxxxxxxx

            interface:
                       id: Bridge0
                     name: Home
              description: Home VLAN

              expires: 0
           registered: yes
               access: permit
             schedule:
               active: no
              rxbytes: 0
              txbytes: 0
               uptime: 0
                 link: down
            ever-seen: yes

        traffic-shape:
                       rx: 0
                       tx: 0
                     mode: mac
                 schedule:

        ''', 2),
        ('''
             host: 
                  mac: 74:ff:ff:ff:ff:ff
                  via: 74:ff:ff:ff:ff:ff
                   ip: 250:250:250:218
             hostname: foxel-desktop
                 name: foxel-desktop

            interface: 
                       id: Bridge0
                     name: Home
              description: Home network

              expires: 0
           registered: yes
               access: permit
             schedule: 
               active: yes
              rxbytes: 3664009359
              txbytes: 280968424
               uptime: 354617
           first-seen: 656249
            last-seen: 1
                 link: up
     auto-negotiation: yes
                speed: 1000
               duplex: yes

        traffic-shape: 
                       rx: 0
                       tx: 0
                     mode: none
                 schedule: 

           mac-access, id = Bridge0: deny

             host: 
                  mac: 10:ff:ff:ff:ff:ff
                  via: 10:ff:ff:ff:ff:ff
                   ip: 250:250:250:200
             hostname: foxhome-server
                 name: foxhome, server

            interface: 
                       id: Bridge0
                     name: Home
              description: Home network

              expires: 0
           registered: yes
               access: permit
             schedule: 
               active: yes
              rxbytes: 2077239992
              txbytes: 665641019
               uptime: 614018
           first-seen: 656255
            last-seen: 1
                 link: up
     auto-negotiation: yes
                speed: 1000
               duplex: yes

        traffic-shape: 
                       rx: 0
                       tx: 0
                     mode: none
                 schedule: 

           mac-access, id = Bridge0: deny

             host: 
                  mac: a4:ff:ff:ff:ff:ff
                  via: a4:ff:ff:ff:ff:ff
                   ip: 250:250:250:224
             hostname: Chromecast-Audio
                 name: foxcast-bedroom
          description: This is very long description with newline 
                       and colon: foo

            interface: 
                       id: Bridge0
                     name: Home
              description: Home network

              expires: 670979
           registered: yes
               access: permit
             schedule: 
               active: yes
              rxbytes: 48388740
              txbytes: 10987076
               uptime: 23108
           first-seen: 656255
            last-seen: 1
                 link: up
     auto-negotiation: yes
                speed: 1000
               duplex: yes

        traffic-shape: 
                       rx: 0
                       tx: 0
                     mode: none
                 schedule: 

           mac-access, id = Bridge0: deny

             host: 
                  mac: a4:ff:ff:ff:ff:ff
                  via: a4:ff:ff:ff:ff:ff
                   ip: 250:250:250:220
             hostname: Chromecast-Audio
                 name: foxcast-kitchen

            interface: 
                       id: Bridge0
                     name: Home
              description: Home network

              expires: 679721
           registered: yes
               access: permit
             schedule: 
               active: yes
              rxbytes: 531016115
              txbytes: 27461293
               uptime: 23482
           first-seen: 656238
            last-seen: 1
                 link: up
                 ssid: FOXHOME-5G
                   ap: WifiMaster1/AccessPoint0
        authenticated: yes
               txrate: 200
                   ht: 40
                 mode: 11ac
                   gi: 400
                 rssi: -57
                  mcs: 9
                 txss: 1

        traffic-shape: 
                       rx: 0
                       tx: 0
                     mode: none
                 schedule: 

           mac-access, id = Bridge0: permit

        ''', 4)
    ]

    return samples[request.param]

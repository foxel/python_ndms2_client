import os
import sys
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from ndms2_client.command import Command
from ndms2_client.connection import HttpConnection


@pytest.fixture
def connection():
    con = HttpConnection("192.168.111.111", 80, "admin", "admin")
    mock = MagicMock()
    mock.read.return_value = b"{}"
    con._open = MagicMock(wraps=Mock(return_value=mock))
    return con


@pytest.mark.parametrize(
    ("command", "url"),
    [
        (Command.VERSION, "/rci/show/version/"),
        (Command.ARP, "/rci/show/ip/arp/"),
        (Command.ASSOCIATIONS, "/rci/show/associations/"),
        (Command.HOTSPOT, "/rci/show/ip/hotspot/"),
        (Command.INTERFACES, "/rci/show/interface/"),
    ],
)
@patch.object(HttpConnection, "connected", new_callable=PropertyMock)
def test_something(mocked_connected, connection, command, url):
    full_url = f"{connection._scheme}://{connection._host}:{connection._port}{url}"
    mocked_connected.return_value = True
    connection.run_command(command)
    connection._open.assert_called_once()
    connection._open.assert_called_with(full_url)

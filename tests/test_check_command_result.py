import os
import sys
from typing import Tuple, List

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# noinspection PyProtectedMember
def test_check_command_result_positive(positive_results: List[str]) -> None:
    from ndms2_client.client import _check_command_result

    assert _check_command_result(positive_results) is positive_results


def test_check_command_result_error(error_results: List[str]) -> None:
    from ndms2_client.client import _check_command_result

    with pytest.raises(Exception):
        _check_command_result(error_results)


@pytest.fixture(params=range(2))
def positive_results(request) -> List[str]:
    data = [
        ['Network::Interface::Base: "WifiMaster0/AccessPoint1": interface is up.'],
        ['Core::System::StartupConfig: Saving (cli).']
    ]
    return data[request.param]


@pytest.fixture(params=range(3))
def error_results(request) -> List[str]:
    data = [
        ['Command::Base error[7405602]: argument parse error.'],
        ['Core::Configurator error[1179653]: interface down: execute denied [cli].'],
        ['Network::Interface::Base error[6553609]: unable to find GuestWiF as "Network::Interface::Base".']
    ]
    return data[request.param]

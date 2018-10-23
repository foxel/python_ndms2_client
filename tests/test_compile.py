#!/usr/bin/python3
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# this is a dummy test showing that code compiles
def test_compile():
    from ndms2_client import TelnetConnection, Client

    assert TelnetConnection is not None
    assert Client is not None

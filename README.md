[![Build Status](https://travis-ci.com/foxel/python_ndms2_client.svg?branch=master)](https://travis-ci.com/foxel/python_ndms2_client)

### Keenetic NDMS v2 client library ###

#### Usage

- Telnet

```python
from ndms2_client import Client, TelnetConnection

client = Client(connection=TelnetConnection("192.168.1.1", 23, "admin", "admin"))
client.get_router_info()
```

- Http

```python
from ndms2_client import Client, HttpConnection

client = Client(connection=HttpConnection("192.168.1.1", 80, "admin", "admin"))
client.get_router_info()
```

#### Tests

```shell
pytest
```

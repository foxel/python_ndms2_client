import hashlib
import json
import logging
from contextlib import suppress
from http.cookiejar import CookieJar
from typing import List
from urllib import request
from urllib.error import HTTPError

from ..command import Command
from .base import Connection, ConnectionException, ResponseConverter

_LOGGER = logging.getLogger(__name__)


class HttpResponseConverter(ResponseConverter):
    def convert(self, command, data):
        if command == Command.INTERFACES:
            return list(data.values())
        return data


class HttpConnection(Connection):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        *,
        scheme: str = "http",
        timeout: int = 30,
        response_converter: ResponseConverter = None,
    ):
        self._scheme = scheme
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._auth_url = f"{scheme}://{self._host}:{self._port}/auth"
        self._converter = response_converter or HttpResponseConverter()
        self._cookie_jar = CookieJar()
        opener = request.build_opener(request.HTTPCookieProcessor(self._cookie_jar))
        request.install_opener(opener)

    @property
    def connected(self) -> bool:
        with suppress(HTTPError):
            response = request.urlopen(self._auth_url)
            return response.status == 200
        return False

    def connect(self):
        message = None
        try:
            try:
                request.urlopen(self._auth_url)
            except HTTPError as error:
                realm = error.headers.get("X-NDM-Realm")
                challenge = error.headers.get("X-NDM-Challenge")

                md5 = hashlib.md5(f"admin:{realm}:{self._password}".encode()).hexdigest()
                sha = hashlib.sha256(f"{challenge}{md5}".encode()).hexdigest()

                req = request.Request(
                    self._auth_url,
                    method="POST",
                    data=json.dumps({"login": "admin", "password": sha}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                response = request.urlopen(req)
                if response.status == 200:
                    return
                message = "Error connecting to api: %s %s" % (response.status, response.read())

        except Exception as e:
            message = "Error connecting to api server: %s" % str(e)
        _LOGGER.error(message)
        raise ConnectionException(message) from None

    def disconnect(self):
        self._cookie_jar.clear()

    def run_command(self, command: Command, name: str = None) -> List[str]:
        if not self.connected:
            self.connect()
        cmd = command.value.replace(" ", "/")
        if name:
            if "/" in name:
                name, *_ = name.split("/")
            cmd = cmd % name
        response = request.urlopen(f"{self._scheme}://{self._host}:{self._port}/rci/{cmd}/")
        response = json.loads(response.read())
        if self._converter:
            return self._converter.convert(command, response)
        return response

import hashlib
import logging
from typing import Optional, List

from .base import ResponseConverter, ConnectionException, Connection
from ..command import Command
from requests import Session, Response

_LOGGER = logging.getLogger(__name__)


class HttpResponseConverter(ResponseConverter):
    def convert(self, command, data):
        if command == Command.INTERFACES:
            return list(data.values())
        return data


class HttpConnection(Connection):

    def __init__(
        self, host: str, port: int, username: str, password: str, *, scheme: str = "http", timeout: int = 30, response_converter: ResponseConverter = None
    ):
        self._session = Session()
        self._scheme = scheme
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._auth_url = f'{scheme}://{self._host}:{self._port}/auth'
        self._converter = response_converter

    @property
    def connected(self) -> bool:
        r = self._session.get(self._auth_url)
        return r.status_code == 200

    def connect(self):
        response: Optional[Response] = None
        try:
            response = self._session.get(self._auth_url)
            if response.ok:
                return
            if response.status_code == 401:
                realm, challenge = response.headers['X-NDM-Realm'], response.headers['X-NDM-Challenge']
                md5 = hashlib.md5(f"{self._username}:{realm}:{self._password}".encode())
                sha = hashlib.sha256(f"{challenge}{md5.hexdigest()}".encode())
                response = self._session.post(
                    self._auth_url, json={
                        "login": self._username,
                        "password": sha.hexdigest()
                    }
                )
                if response.status_code == 200:
                    return
        except Exception as e:
            message = "Error connecting to api server: %s" % str(e)
            if response is not None:
                message = "Error connecting to api: %s %s" % (response.status_code, response.text)
            _LOGGER.error(message)
            raise ConnectionException(message) from None

    def disconnect(self):
        self._session.delete(self._auth_url)

    def run_command(self, command: Command, name: str = None) -> List[str]:
        if not self.connected:
            self.connect()
        cmd = command.value.replace(' ', '/')
        if name:
            if '/' in name:
                name, *_ = name.split("/")
            cmd = cmd % name
        response = self._session.get(f'{self._scheme}://{self._host}:{self._port}/rci/{cmd}/')
        if self._converter:
            return self._converter.convert(command, response.json())
        return response.json()

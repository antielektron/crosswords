import datetime as dt
from . import json_websockets
from . import crossword


class Session(object):
    def __init__(self, days_to_expire: int = 2) -> None:
        self.crossword = None
        self.datetime_created = dt.datetime.utcnow()
        self.connected_sockets = set()
        self.last_touched = self.datetime_created
        self.days_to_expire = 2

    def cleanup(self):
        sockets_to_remove = []
        for socket in self.connected_sockets:
            if socket.is_closed():
                sockets_to_remove.append(socket)

        for socket in sockets_to_remove:
            self.connected_sockets.remove(socket)

    def connect_socket(self,
                       websocket: json_websockets.JsonWebsocketConnection) -> None:

        self.cleanup()
        self.connected_sockets.add(websocket)

    def disconnect_socket(self,
                          websocket: json_websockets.JsonWebsocketConnection) -> None:
        if websocket in self.connected_sockets:
            self.connected_sockets.remove(websocket)

    def get_sockets(self) -> json_websockets.JsonWebsocketConnection:
        self.cleanup()
        return self.connected_sockets

    def get_datetime_created(self) -> dt.datetime:
        return self.datetime_created

    def create_crossword(self, width: int = 20, height: int = 20, lang: str = "en", difficulty: int = 0):
        self.crossword = crossword.Crossword(width=width,
                                             height=height,
                                             lang_code=lang,
                                             difficulty=difficulty)

    def get_crossword(self, lang: str = "en", difficulty: int = 0) -> crossword.Crossword:
        if self.crossword is None:
            self.create_crossword(lang=lang, difficulty=difficulty)

        return self.crossword

    def touch(self):
        self.last_touched = dt.datetime.utcnow()

    def is_expired(self):
        self.cleanup()
        if len(self.connected_sockets) > 0:
            return False
        now = dt.datetime.utcnow()
        if (now - self.last_touched).days > self.days_to_expire:
            return True

        return False

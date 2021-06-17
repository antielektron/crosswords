import datetime as dt
from . import json_websockets
from . import crossword


class Session(object):
    def __init__(self) -> None:
        self.crossword = None
        self.datetime_created = dt.datetime.utcnow()
        self.connected_sockets = set()
    
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

    def create_crossword(self, width: int = 30, height: int = 30):
        self.crossword = crossword.Crossword(width=width,
                                             height=height,
                                             lang_code="en")

    def get_crossword(self) -> crossword.Crossword:
        if self.crossword is None:
            self.create_crossword()
        
        return self.crossword

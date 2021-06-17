from . import json_websockets
from . import crossword_connection

server = json_websockets.JsonWebsocketServer(
    crossword_connection.CrosswordConnection
)
server.run()
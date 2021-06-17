import ssl
import logging
from . import json_websockets
from . import crossword_connection

try:
    cert_file = "./server/fullchain.pem"
    key_file = "./server/privkey.pem"

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_file, keyfile=key_file)
except Exception as e:
    logging.error("no ssl context available: %s", str(e))
    ssl_context = None


server = json_websockets.JsonWebsocketServer(
    crossword_connection.CrosswordConnection, ssl_context=ssl_context
)


server.run()

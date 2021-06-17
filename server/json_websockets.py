import websockets
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)

class JsonWebsocketConnection(object):

    def __init__(self,
                 websocket: websockets.WebSocketServerProtocol):
        
        logging.info("incoming connection")
        self._websocket = websocket
        self._is_closed = False;
    
    def is_closed(self):
        return self._is_closed
    
    async def close(self):
        logging.info("closing connection")
        try:
            if self._is_closed:
                return
            self._websocket.close()
            self._is_closed = True
        except Exception as e:
            logging.warning("error closing connection: %s", str(e))
    
    async def send(self, message: dict):
        string_message = json.dumps(message)
        logging.debug("sending message: %s", string_message)
        try:
            await self._websocket.send(string_message)
        except Exception as e:
            logging.warning("error sending message: %s", str(e))
    
    async def handle_message(self, message: dict):
        pass # override this function

    async def run(self):
        try:
            async for message in self._websocket:
                try:
                    json_message = json.loads(message)
                    await self.handle_message(json_message) 
                except ValueError as e:
                    logging.warning("received unprocessable message %s", str(e))
                
        
        except Exception as e:
                logging.warning("error in websocket connection: %s", str(e))
                self._is_closed = True
        finally:
            self._is_closed = True
        
        



class JsonWebsocketServer(object):
    def __init__(self, handler_class: JsonWebsocketConnection, host:str = 'localhost', port:int = 8765, ssl_context = None):
        self._host = host
        self._port = port
        self._handler_class = handler_class
        self._ssl_context = ssl_context

    def run(self):
        async def main(websocket: websockets.WebSocketServerProtocol,
                       path: str):

            connection = self._handler_class(websocket)

            await connection.run()

        if (self._ssl_context is not None):
            start_server = websockets.serve(main, self._host, self._port, ssl=self._ssl_context)
        else:
            start_server = websockets.serve(main, self._host, self._port)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
        


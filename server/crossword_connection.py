import logging
import uuid

import datetime as dt

from . import json_websockets
from . import session


class CrosswordConnection(json_websockets.JsonWebsocketConnection):

    sessions = {}

    last_cleanup = None

    def clean_sessions():
        now = dt.datetime.utcnow()
        if CrosswordConnection.last_cleanup is None or (now - CrosswordConnection.last_cleanup).total_seconds() > 3600:
            CrosswordConnection.last_cleanup = now

            sessions_to_close = []
            for key, session in CrosswordConnection.sessions.items():
                if session.is_expired():
                    sessions_to_close.append(key)

            for key in sessions_to_close:
                del(CrosswordConnection.sessions[key])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session = None

    async def send_crossword(self, sessionId: str, lang: str = "en", difficulty: int = 0):
        if sessionId not in CrosswordConnection.sessions:
            await self.send_error(msg="unknown session")
            return

        sess = CrosswordConnection.sessions[sessionId]

        # NOTE: if there will be the possibility of private
        # sessions, this has to be changed since this is leaking
        # the information that a certain session exists!
        if self not in sess.get_sockets():
            await self.send_error(msg="you are not registered to given session")
            return

        crossword = sess.get_crossword(lang=lang, difficulty=difficulty)
        await self.send({
            'type': 'crossword',
            'crossword': crossword.serialize()
        })

        # sending also the status as update:
        await self.send({
            'type': 'update',
            'updates': crossword.get_status()
        })

    async def user_update(self, x: int, y: int, letter: str):
        if len(letter) > 1:
            await self.send_error(msg="received invalid userinput")
            return

        update_message = self._session.get_crossword().user_input(x=x, y=y, letter=letter)

        for connection in self._session.get_sockets():
            await connection.send({
                'type': 'update',
                'updates': update_message
            })

    async def register(self, sessionId: str = None, lang: str = "en", difficulty: int = 0):

        if sessionId is None:

            sessionId = uuid.uuid4().hex
            while sessionId in CrosswordConnection.sessions:
                sessionId = uuid.uuid4().hex

            new_session = session.Session()
            CrosswordConnection.sessions[sessionId] = new_session

        if sessionId not in CrosswordConnection.sessions:
            await self.send_error("unknown session id")

            # register with new id:
            await self.register(lang=lang, difficulty=difficulty)
            return

        sess = CrosswordConnection.sessions[sessionId]
        sess.connect_socket(self)

        self._session = sess

        await self.send({
            'type': 'register',
            'sessionId': sessionId
        })

        await self.send_crossword(sessionId, lang=lang, difficulty=difficulty)

        # clean up old session
        CrosswordConnection.clean_sessions()

    async def send_error(self, msg: str):
        await self.send({
            'type': 'error',
            'message': msg
        })

    async def handle_message(self, message: dict):
        logging.info("incoming message: %s", str(message))
        if not "type" in message:
            logging.error("received malformated message")
            await self.send_error(msg="i do not understand the request")
            return

        if message['type'] == 'register':
            sessionId = None
            lang = "en"
            difficulty = 0
            if 'sessionId' in message:
                sessionId = message['sessionId']
            if "lang" in message:
                lang = message['lang']
            if "difficulty" in message:
                difficulty = message["difficulty"]
            await self.register(sessionId=sessionId, lang=lang, difficulty=difficulty)
            return

        if self._session is None:
            await self.send_error(msg="you are not registered properly")
            return

        if message['type'] == "update":
            await self.user_update(x=message['x'], y=message['y'], letter=message['letter'])
            return

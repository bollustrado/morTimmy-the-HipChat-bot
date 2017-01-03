#!/usr/bin/env python3

import asyncio
from aiohttp import web, MultiDict, ClientSession, BasicAuth
import ssl
import logging
from .utils import print_json
import json

logger = logging.getLogger(__name__)


class Bot:

    def __init__(self,
                 name="morTimmy", description='The coolest bot in town',
                 host="new.mortimer.nl", port=6666,
                 loop=None,
                 in_global=False, in_room=True,
                 ssl_crt='/home/mortimerm/development/morTimmy-the-HipChat-bot/mortimmy/new.mortimer.nl.crt',
                 ssl_key='/home/mortimerm/development/morTimmy-the-HipChat-bot/mortimmy/new.mortimer.nl.key'):
        """Initialise bot

        :param name: Name of the bot/application
        :param description: Description of the bot/appication
        :param host: IP or hostname to listen on
        :param port: TCP port number to listen on
        :param loop: Asyncio loop to utilise
        :param in_global: Can the bot be installed globally
        :param in_room: Can the bot be installed in a room
        """

        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.in_global = in_global
        self.in_room = in_room
        self.ssl_crt = ssl_crt
        self.ssl_key = ssl_key

        self.bot_url = "https://{}:{}/".format(host, port)

        # TODO: These list should be replaced by permanent storage(e.g sqlite)
        self.installations = {}
        self.access_tokens = {}

        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()

        self.app = web.Application(loop=self.loop)
        self.register_routes()

    async def start_background_tasks(self, app):
        """Starts any required background tasks"""
        app['refresh_access_tokens'] = app.loop.create_task(self.refresh_access_tokens(app))
        app['test_notifications'] = app.loop.create_task(self.test_notifications(app))

    async def cleanup_background_tasks(self, app):
        """Cleans up after any running background tasks"""
        app['refresh_access_tokens'].cancel()
        await app['refresh_access_tokens']

        app['test_notifications'].cancel()
        await app['test_notifications']

    def start(self):
        """Starts the HipChat bot"""

        # Initialise SSL certificate for HTTPS daemon
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ssl_context.load_cert_chain(self.ssl_crt, keyfile=self.ssl_key)

        # Register background tasks
        self.app.on_startup.append(self.start_background_tasks)
        self.app.on_cleanup.append(self.cleanup_background_tasks)

        # Run the HTTPS daemon
        web.run_app(
            self.app,
            host=self.host,
            port=self.port,
            ssl_context=ssl_context
        )

    def register_routes(self):
        """Registers all HTTP routes"""
        logger.debug('Adding route GET /capabilities')
        self.app.router.add_route('GET', '/capabilities', self.capabilities_descriptor)
        logger.debug('Adding route POST /installer')
        self.app.router.add_route('POST', '/installer', self.installer)
        logger.debug('Adding route POST /uninstaller')
        self.app.router.add_route('POST', '/uninstaller', self.uninstaller)

    async def refresh_access_tokens(self, app):
        """Handles non-existing or expiring access tokens for all installations"""
        try:
            while True:
                await asyncio.sleep(10)

                if self.installations:
                    logging.debug('Checking for missing or expiring access tokens')
                    for oauth_id in self.installations.keys():
                        if oauth_id not in self.access_tokens:
                            logging.debug('Installation {} has no access token'.format(oauth_id))
                            await self.get_access_token(oauth_id)

        except asyncio.CancelledError:
            pass

    async def test_notifications(self, app):
        """Sends a test noticification to a room every 10sec"""
        try:
            while True:
                await asyncio.sleep(10)

                if self.installations and self.access_tokens:
                    logging.debug('Sending test notification')
                    for oauth_id in self.installations.keys():
                        await self.send_message(oauth_id, '3441596', 'Hello World!')
        except asyncio.CancelledError:
            pass

    async def get_access_token(self, oauth_id):
        """Retrieves an access token from HipChat server

        These tokens typically expire after one hour.

        :param oauth_id: The oAuth ID to retrieve a token for
        """

        installation = self.installations[oauth_id]

        payload = "grant_type=client_credentials"
        auth = BasicAuth(installation['oauthId'], installation['oauthSecret'])
        headers = MultiDict({'Content-Type': 'application/x-www-form-urlencoded'})

        logging.debug('Retrieving access token for oauth_id {}'.format(oauth_id))
        async with ClientSession(loop=self.loop) as session:
            async with session.post(installation['tokenUrl'], auth=auth, data=payload, headers=headers) as response:
                data = await response.json()

                self.access_tokens[oauth_id] = data

    async def send_message(self, oauth_id, room_id, message, html=True):
        """Sends a message to a room

        :param oauth_id: The ID of the installation
        :param room_id: The ID of the room
        :param message: The message to send
        :param html: Is the message HTML formatted
        """
        installation = self.installations[oauth_id]
        notification_url = "{}room/{}/notification".format(installation['apiUrl'], room_id)
        headers = MultiDict(
            {
                'Authorization': 'Bearer {}'.format(self.access_tokens[oauth_id]['access_token']),
                'Content-Type': 'application/json'
            }
        )
        payload = {
                'message': message,
                'notify': False,
                'color': 'gray'
        }

        if html:
            payload['message_format'] = 'html'
        else:
            payload['message_format'] = ' text'

        logging.debug('Sending message {} to room id {}'.format(message, room_id))
        async with ClientSession(loop=self.loop) as session:
            async with session.post(notification_url, data=json.dumps(payload), headers=headers) as response:
                data = await response.text()
                print(data)

    async def capabilities_descriptor(self, request):
        """Returns the bot capabilities to the HipChat server"""

        logger.debug('Received {} {}'.format(request.method, request.path))

        capabilities = {
            "name": self.name,
            "description": self.description,
            "key": self.name,
            "links": {
                "homepage": self.bot_url,
                "self": "{}capabilities".format(self.bot_url)
            },
            "capabilities": {
                "hipchatApiConsumer": {
                    "scopes": [
                        "send_notification"
                    ]
                },
                "installable": {
                        "allowGlobal": self.in_global,
                        "allowRoom": self.in_room,
                        "callbackUrl": "{}installer".format(self.bot_url),
                        "uninstalledUrl": "{}uninstaller".format(self.bot_url)
                }
            }
        }

        return web.json_response(capabilities, status=200)

    async def installer(self, request):
        """The installer endpoint

        This endpoint gets called by the HipChat server everytime a user installs
        the app/bot

        :return: HTTP status 204
        """
        data = await request.json()
        logger.debug('Received POST {}, payload {}'.format(self.bot_url + 'installed', data))

        # Retrieve the token and API endpoint URL from HipChat server
        logger.debug('Retrieving capabilities from HipChat server')
        async with ClientSession(loop=self.loop) as session:
            async with session.get(data['capabilitiesUrl']) as response:
                capabilities = await response.json()

                data['tokenUrl'] = capabilities['capabilities']['oauth2Provider']['tokenUrl']
                data['apiUrl'] = capabilities['capabilities']['hipchatApiProvider']['url']

        logger.debug('Storing installation data')
        self.installations[data['oauthId']] = data

        # TODO Move this out of here
        # We should check for the presence of a (valid) token
        # for each installation in a async loop somewhere
        # and request/renew the access token there
        #logger.debug('Retrieving access token')
        #await self.get_access_token(data['oauthId'])

        return web.Response(status=204)

    async def uninstaller(self, request):
        """The installer endpoint

        This endpoint gets called by the HipChat server everytime a user uninstalls
        the app/bot

        :return: HTTP redirect to HipChat redirectUrl
        """
        data = await request.json()
        logger.debug('Received POST {}, payload {}'.format(self.bot_url + 'uninstalled', data))

        logger.debug('Retrieving capabilities from HipChat server')
        async with ClientSession(loop=self.loop) as session:
            async with session.get(data['installableUrl']) as response:
                capabilities = await response.json()

                del self.installations[capabilities['oauthId']]
                del self.access_tokens[capabilities['oauthId']]

        return web.Response(status=302, headers=MultiDict({'Location': data['redirectUrl']}))

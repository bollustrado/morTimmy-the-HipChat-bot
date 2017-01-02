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

    def start(self):
        """Starts the HipChat bot"""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ssl_context.load_cert_chain(self.ssl_crt, keyfile=self.ssl_key)

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

    async def get_access_token(self, oauth_id):
        """Retrieves an access token from HipChat server

        These tokens typically expire after one hour.

        :param oauth_id: The oAuth ID to retrieve a token for
        """

        installation = self.installations[oauth_id]

        payload = "grant_type=client_credentials"
        auth = BasicAuth(installation['oauthId'], installation['oauthSecret'])
        headers = MultiDict({'Content-Type': 'application/x-www-form-urlencoded'})

        async with ClientSession(loop=self.loop) as session:
            async with session.post(installation['tokenUrl'], auth=auth, data=payload, headers=headers) as response:
                data = await response.json()

                self.access_tokens[oauth_id] = data

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

        logger.debug('Retrieving access token')
        await self.get_access_token(data['oauthId'])

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

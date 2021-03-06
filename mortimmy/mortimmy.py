#!/usr/bin/env python3

import time
import asyncio
from aiohttp import web, MultiDict, ClientSession, BasicAuth
import ssl
import logging
from .utils import print_json
import json

logger = logging.getLogger(__name__)

# TODO Create a decorator that validates the JWT tokens on each incoming request


class HipChat:
    """Object for working with (non add-on) HipChat REST API"""
    pass


class WebHook:
    """Object containing parameters for a single webhook"""

    def __init__(self, name, base_url, event, pattern=None, authentication=None):
        """A WebHook object

        :param name: name of the webhook. Will be used in the url
        :param base_url: The full url of the HipChat Add-On
        :param event: the webhook event (e.g. room_message)

        :param pattern: regular expression to match on
        :param authentication: None or jwt
        """
        self.name = name
        # TODO Perhaps use a getter/setter for self.url so the hipchat add-on can set this
        # when compiling the capabilities descriptor?
        self.url = "{}/{}".format(base_url, name.lower())

        if event not in ("room_archived", "room_created", "room_deleted", "room_enter",
                "room_exit", "room_file_upload", "room_message", "room_notification",
                "room_topic_change", "room_unarchived"):
            raise ValueError("WebHook {} incorrect event type {}".format(name, event))

        self.event = event

        if authentication is None:
            self.authentication = 'none'
        elif authentication == 'jwt' or authentication == 'none':
            self.authentication = authentication
        else:
            raise ValueError("WebHook {} authentication should be None or 'jwt'".format(name))

        self.pattern = pattern

    def capabilities(self):
        """Returns JSON webhook entry for addition in capabilities descriptor"""
        data = {
            "url": self.url,
            "event": self.event,
            "authentication": self.authentication,
            "name": self.name
        }

        if self.event in ('room_message', 'room_notification'):
            data['pattern'] = self.pattern

        return data

    async def incoming(self, request):
        """Incoming WebHook Post Request

        :param request: aiohttp json request
        """
        # TODO, perhaps we should call a webhook class function here
        # that will parse the awaited data. This function
        # should be overwritten by all the Add On webhook subclasses
        # allowing for simple plugins. If we don't do any
        # blocking stuff in the plugin we could perhaps get
        # away with non asyncio plugins. Best would be if we somehow
        # can do both, perhaps have to have a asyncio and non-asyncio
        # webhook class or make it a bolean option in the __init__
        data = await request.json()
        # logger.debug('Received POST {}, payload {}'.format(self.url, data))

        response = {
            'message': '<h1>Hello World!</h1>',
            'notify': False,
            'color': 'gray',
            'message_format': 'html'
        }
        print_json(response)

        return web.json_response(response, status=204)


class Glance:
    def capabilities(self):
        pass


class Sidebar:
    def capabilities(self):
        pass


class AddOn:
    """Object for running a HipChat Add-On"""

    def __init__(self,
                 name, description,
                 host, port,
                 ssl_crt, ssl_key,
                 database,
                 webhooks=[],
                 glances=[],
                 sidebars=[],
                 loop=None,
                 in_global=False, in_room=True,
                 avatar_url=None, avatar_url_hi=None):
        """Initialise Add-On

        :param name: Name of the Add-On
        :param description: Description of the Add-On
        :param host: IP or hostname to listen on
        :param port: TCP port number to listen on
        :param database: The installation/token database class

        :param webhooks: list of `class`:Webhook
        :param glances: list of `class`:Glance
        :param sidebars: list of `class`:Sidebar

        :param loop: Asyncio loop to utilise
        :param in_global: Can the Add-On be installed globally
        :param in_room: Can the Add-On be installed in a room
        :param avatar_url: Avatar image url
        :param avatar_url_hi: @2x (high dpi) avatar image url
        """

        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.in_global = in_global
        self.in_room = in_room
        self.ssl_crt = ssl_crt
        self.ssl_key = ssl_key
        self.db = database

        self.avatar_url = avatar_url
        self.avatar_url_hi = avatar_url_hi

        self.webhooks = webhooks
        self.glances = glances
        self.sidebars = sidebars

        self.addon_url = "https://{}:{}/".format(host, port)

        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()

        self.app = web.Application(loop=self.loop)
        self.register_routes()

    async def start_background_tasks(self, app):
        """Starts any required background tasks"""
        app['refresh_access_tokens'] = app.loop.create_task(self.refresh_access_tokens(app))
        # app['test_notifications'] = app.loop.create_task(self.test_notifications(app))

    async def cleanup_background_tasks(self, app):
        """Cleans up after any running background tasks"""
        app['refresh_access_tokens'].cancel()
        await app['refresh_access_tokens']

        # app['test_notifications'].cancel()
        # await app['test_notifications']

    def start(self):
        """Starts the HipChat Add-On"""

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
        """Register all HTTP routes"""
        logger.debug('Adding route GET /capabilities')
        self.app.router.add_route('GET', '/capabilities', self.capabilities_descriptor)
        logger.debug('Adding route POST /installer')
        self.app.router.add_route('POST', '/installer', self.installer)
        logger.debug('Adding route POST /uninstaller')
        self.app.router.add_route('GET', '/uninstaller', self.uninstaller)

        for webhook in self.webhooks:
            logger.debug('Adding route POST /{}'.format(webhook.name))
            self.app.router.add_route('POST', '/{}'.format(webhook.name), webhook.incoming)

    async def refresh_access_tokens(self, app):
        """Handles non-existing or expiring access tokens for all installations"""
        try:
            while True:
                await asyncio.sleep(10)

                installations = self.db.read_installations()
                access_tokens = self.db.read_access_tokens()

                if installations:
                    logging.debug('Checking for missing or expiring access tokens')

                    for oauth_id in installations.keys():
                        time_to_renew = time.time() - 300

                        if oauth_id not in access_tokens:
                            logging.debug('Installation {} has no access token'.format(oauth_id))
                            await self.get_access_token(oauth_id)

                        elif access_tokens[oauth_id]['expires_at'] < time_to_renew:
                            logging.debug('Installation {} will expire soon'.format(oauth_id))
                            await self.get_access_token(oauth_id)

        except asyncio.CancelledError:
            pass

    async def test_notifications(self, app):
        """Sends a test noticification to a room every 10sec"""
        try:
            while True:
                await asyncio.sleep(10)

                installations = self.db.read_installations()
                access_tokens = self.db.read_access_tokens()

                if installations and access_tokens:
                    for oauth_id in installations.keys():
                        await self.send_message(oauth_id, '3441596', 'Hello World!')

        except asyncio.CancelledError:
            pass

    async def get_access_token(self, oauth_id):
        """Retrieves an access token from HipChat server

        These tokens typically expire after one hour.

        :param oauth_id: The oAuth ID to retrieve a token for
        """

        installation = self.db.read_installation(oauth_id)

        payload = "grant_type=client_credentials"
        auth = BasicAuth(oauth_id, installation['oauthSecret'])
        headers = MultiDict({'Content-Type': 'application/x-www-form-urlencoded'})

        logging.debug('Retrieving access token for oauth_id {}'.format(oauth_id))
        async with ClientSession(loop=self.loop) as session:
            async with session.post(installation['tokenUrl'],
                                    auth=auth,
                                    data=payload,
                                    headers=headers) as response:
                data = await response.json()

                # Calculating expiration time minus 60sec for a bit of leeway
                try:
                    data['expires_at'] = time.time() + int(data['expires_in']) - 60
                except KeyError:
                    logging.debug('Error getting access token, HipChat response: {}'.format(data))
                    exit(-1)

                self.db.write_access_token(oauth_id, data)

    async def send_message(self, oauth_id, room_id, message, html=True):
        """Sends a message to a room

        :param oauth_id: The ID of the installation
        :param room_id: The ID of the room
        :param message: The message to send
        :param html: Is the message HTML formatted
        """
        installation = self.db.read_installation(oauth_id)
        access_token = self.db.read_access_token(oauth_id)

        notification_url = "{}room/{}/notification".format(installation['apiUrl'], room_id)
        headers = MultiDict(
            {
                'Authorization': 'Bearer {}'.format(access_token['access_token']),
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
            async with session.post(notification_url,
                                    data=json.dumps(payload),
                                    headers=headers) as response:
                data = await response.text()

    async def capabilities_descriptor(self, request):
        """Returns the Add-On capabilities to the HipChat server"""

        logger.debug('Received {} {}'.format(request.method, request.path))

        capabilities = {
            "name": self.name,
            "description": self.description,
            "key": self.name,
            "links": {
                "homepage": self.addon_url,
                "self": "{}capabilities".format(self.addon_url)
            },
            "capabilities": {
                "hipchatApiConsumer": {
                    "scopes": [
                        "send_notification",
                        "admin_room",
                        "send_message",
                        "view_messages",
                        "view_group"
                    ]
                },
                "installable": {
                        "allowGlobal": self.in_global,
                        "allowRoom": self.in_room,
                        "callbackUrl": "{}installer".format(self.addon_url),
                        "uninstalledUrl": "{}uninstaller".format(self.addon_url)
                }
            }
        }

        capabilities['capabilities']['webhook'] = [webhook.capabilities() for webhook in self.webhooks]
        capabilities['capabilities']['glance'] = [glance.capabilities() for glance in self.glances]
        capabilities['capabilities']['webPanel'] = [sidebar.capabilities() for sidebar in self.sidebars]

        return web.json_response(capabilities, status=200)

    async def installer(self, request):
        """The installer endpoint

        This endpoint gets called by the HipChat server everytime a user installs
        the Add-On

        :return: HTTP status 204
        """
        data = await request.json()
        logger.debug('Received POST {}, payload {}'.format(self.addon_url + 'installed', data))

        # Retrieve the token and API endpoint URL from HipChat server
        logger.debug('Retrieving capabilities from HipChat server')
        async with ClientSession(loop=self.loop) as session:
            async with session.get(data['capabilitiesUrl']) as response:
                capabilities = await response.json()

                data['tokenUrl'] = capabilities['capabilities']['oauth2Provider']['tokenUrl']
                data['apiUrl'] = capabilities['capabilities']['hipchatApiProvider']['url']

        logger.debug('Storing installation data')
        self.db.write_installation(data)

        return web.Response(status=204)

    async def uninstaller(self, request):
        """The installer endpoint

        This endpoint gets called by the HipChat server everytime a user uninstalls
        the Add-On

        :return: HTTP redirect to HipChat redirectUrl
        """
        logger.debug('Received GET {}'.format(self.addon_url + 'uninstalled'))

        async with ClientSession(loop=self.loop) as session:
            async with session.get(data['installableUrl']) as response:
                capabilities = await response.json()

                oauth_id = capabilities['oauthId']
                logger.debug('Removing installation and token for oauth_id {}'.format(oauth_id))
                self.db.del_installation(oauth_id)
                self.db.del_access_token(oauth_id)

        return web.Response(status=302, headers=MultiDict({'Location': data['redirectUrl']}))

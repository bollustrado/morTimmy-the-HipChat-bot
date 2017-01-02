#!/usr/bin/env python3

import asyncio
import aiohttp


class Bot:

    def __init__(self, name="morTimmy", host="0.0.0.0", port=6666):
        """Initialise bot
        
        :param name: Name of the bot/application
        :param host: IP or hostname to listen on
        :param port: TCP port number to listen on
        """

        self.host = host
        self.port = port
        self.name = name

        self.bot_url = "https://{}:{}/{}".format(host, port, name)

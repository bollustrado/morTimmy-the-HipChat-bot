#!/usr/bin/env python3

from mortimmy import AddOn, load_config_file, LocalDB, WebHook
import logging


if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log.main',
                        level=logging.DEBUG,
                        filemode='w',
                        format='%(asctime)s %(levelname)s %(message)s')

    (
        name,  description,
        host, port,
        ssl_crt, ssl_key,
        motd, addon_version, author,
        avatar_url, avatar_url_hi
    ) = load_config_file()

    database = LocalDB()

    slash_commands = WebHook(
        'slashcommands',
        'https://new.mortimer.nl:6666',
        'room_message',
        #pattern='^/[eE][cC][hH][oO]'
        pattern='^/.*'
    )

    morTimmy = AddOn(
        name=name, description=description,
        host=host, port=port,
        ssl_crt=ssl_crt, ssl_key=ssl_key,
        webhooks=[slash_commands],
        database=database,
        avatar_url=avatar_url, avatar_url_hi=avatar_url_hi
    )
    morTimmy.start()

#!/usr/bin/env python3

from mortimmy import Bot, load_config_file
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
        motd, bot_version, author
    ) = load_config_file()

    morTimmy = Bot(
        name=name, description=description,
        host=host, port=port,
        ssl_crt=ssl_crt, ssl_key=ssl_key,
    )
    morTimmy.start()

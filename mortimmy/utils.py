#!/usr/bin/env python3

import json
import time


def load_config_file(filename='config.json'):
    """ Loads credentials from config file """
    with open(filename, 'r') as f:
        config = json.load(f)

    return (
        config[0]['name'],
        config[0]['description'],
        config[0]['host'],
        config[0]['port'],
        config[0]['ssl_crt'],
        config[0]['ssl_key'],
        config[0]['motd'],
        config[0]['addon_version'],
        config[0]['author'],
        config[0]['avatar_url'],
        config[0]['avatar_url_hi']
    )


def calc_uptime(start_timestamp):
    """ Calculate the uptime

    :param start_timestamp: timestamp when launched

    returns string: "days x, minutes y, seconds z"
    """
    uptime_timestamp = time.time() - start_timestamp
    days = uptime_timestamp / 60 / 60 / 24
    hours = (days % 1) * 24
    minutes = (hours % 1) * 60
    seconds = (minutes % 1) * 60

    return ('{} days, {} minutes, {} seconds'
            .format(int(days), int(minutes), int(seconds)))


def print_json(data, sort_keys=True, indent=4):
    print(json.dumps(data,
                     sort_keys=sort_keys,
                     indent=indent,
                     separators=(',', ': ')))

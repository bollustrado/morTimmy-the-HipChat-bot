#!/usr/bin/env python3

import json


def print_json(text):
    """Pretty print json formatted text"""
    print(json.dumps(text, indent=4, sort_keys=True))

def parse_config_json(filename):
    """Read a config.json file"""
    pass

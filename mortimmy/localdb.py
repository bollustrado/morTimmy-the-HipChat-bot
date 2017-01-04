#!/usr/bin/env python3

import json


class LocalDB:
    """A poor mans database, AKA one big json file containing records"""

    def __init__(self,
                 installation_filename='db/installations.json',
                 token_filename='db/tokens.json'):
        """Initialise the local file that will be used as a poor mans database"""
        self.installation_filename = installation_filename
        self.token_filename = token_filename

        # Create empty files if they don't exist yet
        try:
            self.read_installations()
        except FileNotFoundError:
            with open(self.installation_filename, 'w') as f:
                json.dump([{}], f)

        try:
            self.read_access_tokens()
        except FileNotFoundError:
            with open(self.token_filename, 'w') as f:
                json.dump([{}], f)

    def write_installation(self, installation):

        installations = self.read_installations()

        oauth_id = installation['oauthId']
        installations[oauth_id] = installation

        self._file_wr(self.installation_filename, installations)

    def del_installation(self, oauth_id):
        installations = self.read_installations()

        if oauth_id in installations:
            del installations[oauth_id]
            self._file_wr(self.installation_filename, installations)

    def read_installations(self):
        return self._file_r(self.installation_filename)[0]

    def read_installation(self, oauth_id):
        """returns a single installation"""
        installations = self.read_installations()
        return installations.get(oauth_id, None)

    def write_access_token(self, oauth_id, token):
        tokens = self.read_access_tokens()

        tokens[oauth_id] = token

        self._file_wr(self.token_filename, tokens)

    def del_access_token(self, oauth_id):
        tokens = self.read_access_tokens()

        if oauth_id in tokens:
            del tokens[oauth_id]
            self._file_wr(self.token_filename, tokens)

    def read_access_tokens(self):
        return self._file_r(self.token_filename)[0]

    def read_access_token(self, oauth_id):
        """returns a single access_token"""
        tokens = self.read_access_tokens()
        return tokens.get(oauth_id, None)

    def _file_wr(self, filename, data):
        """Helper function to write a file"""
        with open(filename, 'w') as f:
            json.dump([data], f)

    def _file_r(self, filename):
        """Helper function to read a file"""
        with open(filename, 'r') as f:
            data = json.load(f)

        return data

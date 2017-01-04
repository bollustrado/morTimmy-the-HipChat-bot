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

    def write_installation(self, installation):

        installations = self.read_installations()

        oauth_id = installation['oauthId']
        installations[0][oauth_id] = installation

        self._file_wr(self.installation_filename, installations)

    def del_installation(self, oauth_id):
        installations = self.read_installations()

        if oauth_id in installations[0]:
            del installations[0][oauth_id]
            self._file_wr(self.installation_filename, installations)

    def read_installations(self):
        return self._file_r(self.installation_filename)

    def read_installation(self, oauth_id):
        """returns a single installation"""
        installations = self.read_installations()
        return installations[0].get(oauth_id, None)

    def write_access_token(self, token):
        tokens = self.read_access_tokens()
        tokens.append(token)

        oauth_id = token['oauthId']
        tokens[0][oauth_id] = token

        self._file_w(self.token_filename, tokens)

    def del_access_token(self, oauth_id):
        tokens = self.read_access_tokens()

        if oauth_id in tokens[0]:
            del tokens[0][oauth_id]
            self._file_w(self.token_filename, tokens)

    def read_access_tokens(self):
        return self._file_r(self.token_filename)

    def read_access_token(self, oauth_id):
        """returns a single access_token"""
        tokens = self.read_access_tokens()
        return tokens[0].get(oauth_id, None)

    def _file_wr(self, filename, data):
        """Helper function to write a file"""
        with open(filename, 'w') as f:
            json.dump(data, f)

    def _file_r(self, filename):
        """Helper function to read a file"""
        with open(filename, 'r') as f:
            data = json.load(f)

        return data

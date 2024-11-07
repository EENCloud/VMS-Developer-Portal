from flask import session
from app.een_client import TokenStorage


class SessionTokenStorage(TokenStorage):
    def __init__(self):
        self.session = session

    def get(self, key):
        return self.session.get(key)

    def set(self, key, value):
        self.session[key] = value

    def __contains__(self, key):
        return key in self.session

    def remove(self, key):
        if key in self.session:
            del self.session[key]

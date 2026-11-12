"""Fixture for function-catalog tests."""


def read_config(path):
    return path


async def fetch_user(user_id):
    return user_id


def _private_helper():
    return None


class Store:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    async def save_all(self):
        return self.items

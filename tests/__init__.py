import os.path


def data(f: str) -> str:
    current = os.path.dirname(os.path.realpath(__file__))
    return f'{current}/data/{f}'

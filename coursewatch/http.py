import aiohttp
import ssl

CIPHERS = '{defaults}:!DH'.format(defaults=ssl._DEFAULT_CIPHERS)


def create_aiohttp_session():
    ssl_context = ssl.create_default_context()
    ssl_context.set_ciphers(CIPHERS)
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context))

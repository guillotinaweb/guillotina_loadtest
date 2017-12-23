from glt import conf

import aiohttp
import json


async def setup_container(arguments, loop):
    async with aiohttp.ClientSession(loop=loop) as session:
        resp = await session.delete(
            conf.G_URL + '/container',
            auth=aiohttp.BasicAuth('root', 'root'))
        await resp.release()
    async with aiohttp.ClientSession(loop=loop) as session:
        resp = await session.post(
            conf.G_URL,
            auth=aiohttp.BasicAuth('root', 'root'),
            data=json.dumps({
                "id": "container",
                "@type": "Container",
                "title": "Container"}))
        await resp.release()

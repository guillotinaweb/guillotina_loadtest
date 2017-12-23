import aiohttp
import asyncio
import json
import random
import threading


class BuildContent(threading.Thread):
    title = ''

    _max_per_folder = 10

    def __init__(self, url, number):
        self._url = url
        self._number = number
        self._created = 0
        self._updated = 0
        self._loaded = 0
        self._retries = 0
        self._dive = False
        super().__init__(target=self)

    def __call__(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._run())

    async def _run(self):
        await self.crawl_folder(self._url)

    async def update(self, url):
        # print(f'{self._loaded} updating {url}')
        async with aiohttp.ClientSession(loop=self._loop) as session:
            resp = await session.patch(
                url, auth=aiohttp.BasicAuth('root', 'root'),
                data=json.dumps({
                    "title": "Folder updated"}))
            if resp.status == 409:
                # conflict error
                # await asyncio.sleep(0.1)
                self._retries += 1
                return await self.update(url)
            if resp.status != 204:
                print(f'Bad status {resp.status}')
            assert resp.status == 204
            await resp.release()
        self._updated += 1
        self._loaded += 1

    async def write(self, url):
        # print(f'{self._loaded} writing to {url}')
        async with aiohttp.ClientSession(loop=self._loop) as session:
            resp = await session.post(
                url, auth=aiohttp.BasicAuth('root', 'root'),
                data=json.dumps({
                    "@type": "Folder",
                    "title": "Folder"}))
            assert resp.status == 201
            await resp.release()
        self._created += 1
        self._loaded += 1

    async def read(self, url):
        async with aiohttp.ClientSession(loop=self._loop) as session:
            # print(f'{self._loaded} scanning {url}')
            resp = await session.get(
                url, auth=aiohttp.BasicAuth('root', 'root'))
            try:
                data = await resp.json()
            except:
                print(f'error getting response for {url} - diving out')
                return
            assert resp.status == 200
            await resp.release()
            self._loaded += 1
            return data

    async def crawl_folder(self, url):
        if self._dive:
            return

        data = await self.read(url)
        if self._loaded > self._number:
            self._dive = True
            return

        if self._max_per_folder > data['length']:
            await self.write(url)
            if self._loaded > self._number:
                self._dive = True
                return
            await self.crawl_folder(url)
        else:
            for item in data['items']:
                await self.crawl_folder(item['@id'])


class WriteLoadTest(BuildContent):
    title = 'Writes'

    async def _run(self):
        while self._number > self._loaded:
            await self.write(self._url)


class CrawlLoadTest(BuildContent):
    title = 'Crawl'

    async def _run(self):
        while self._number > self._loaded:
            await self.crawl_folder(self._url)

    async def crawl_folder(self, url):
        if self._dive:
            return

        data = await self.read(url)
        if self._loaded > self._number:
            self._dive = True
            return

        for item in data['items']:
            await self.crawl_folder(item['@id'])


class CrawlAndUpdateLoadTest(BuildContent):
    title = 'Crawl and update'

    async def _run(self):
        while self._number > self._loaded:
            await self.crawl_folder(self._url)

    async def crawl_folder(self, url):
        if self._dive:
            return

        data = await self.read(url)
        if self._loaded > self._number:
            self._dive = True
            return

        items = data['items']
        random.shuffle(items)
        for item in items:
            await self.update(item['@id'])
            await self.crawl_folder(item['@id'])


class ContentiousUpdateLoadTest(BuildContent):
    title = 'Contentious update'

    async def _run(self):
        while self._number > self._loaded:
            await self.crawl_folder(self._url)

    async def crawl_folder(self, url):
        if self._dive:
            return

        data = await self.read(self._url)
        url = data['items'][0]['@id']
        while self._number > self._loaded:
            await self.update(url)


class ReadLoadTest(BuildContent):
    title = 'Read'

    async def _run(self):
        data = await self.read(self._url)
        url = data['items'][0]['@id']
        while self._number > self._loaded:
            await self.read(url)

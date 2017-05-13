import argparse
import asyncio
import json
import threading
import time

import aiohttp


class BuildContent(threading.Thread):

    _max_per_folder = 10

    def __init__(self, url, username, password, number):
        self._url = url
        self._username = username
        self._password = password
        self._number = number
        self._created = 0
        self._loaded = 0
        self._dive = False
        super().__init__(target=self)

    def __call__(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._run())

    async def _run(self):
        await self.crawl_folder(self._url)

    async def write(self, url):
        # print(f'{self._loaded} writing to {url}')
        async with aiohttp.ClientSession(loop=self._loop) as session:
            resp = await session.post(
                url, auth=aiohttp.BasicAuth(self._username, self._password),
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
                url, auth=aiohttp.BasicAuth(self._username, self._password))
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
            await self.write(self._url)
            if self._loaded > self._number:
                self._dive = True
                return
            await self.crawl_folder(url)
        else:
            for item in data['items']:
                await self.crawl_folder(item['@id'])


class WriteLoadTest(BuildContent):

    async def _run(self):
        while self._number > self._loaded:
            await self.write(self._url)


class ReadLoadTest(BuildContent):

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


class LoadTester:

    def __init__(self, thread_class, arguments):
        self._thread_class = thread_class
        self._start = 0
        self._end = 0
        self._total_reqs = 0
        self._total_writes = 0
        self._threads = []
        self._arguments = arguments

    def __call__(self):
        self._start = time.time()

        print(f'starting up {self._arguments.concurrency} threads')

        for i in range(self._arguments.concurrency):
            thread = self._thread_class(
                self._arguments.url + '/container', self._arguments.username,
                self._arguments.password, self._arguments.number)
            self._threads.append(thread)
            thread.start()

        print(f'Waiting to finish')

        for thread in self._threads:
            thread.join()
            self._total_reqs += thread._loaded
            self._total_writes += thread._created

        self._end = time.time()

    def stats(self):
        print(f'Total requests: {self._total_reqs}')
        print(f'Total writes: {self._total_writes}')
        print(f'Seconds: {self._end - self._start}')
        print(f'Per sec: {self._total_reqs / (self._end - self._start)}')
        if self._total_writes > 0:
            print(f'Writes per sec: {self._total_writes / (self._end - self._start)}')


async def setup_container(arguments, loop):
    async with aiohttp.ClientSession(loop=loop) as session:
        resp = await session.delete(
            arguments.url + '/container',
            auth=aiohttp.BasicAuth(arguments.username, arguments.password))
        await resp.release()
    async with aiohttp.ClientSession(loop=loop) as session:
        resp = await session.post(
            arguments.url,
            auth=aiohttp.BasicAuth(arguments.username, arguments.password),
            data=json.dumps({
                "id": "container",
                "@type": "Container",
                "title": "Container"}))
        await resp.release()


parser = argparse.ArgumentParser(description='Load test guillotina')
parser.add_argument('--url', default='http://localhost:8080/db')
parser.add_argument('--username', default='root')
parser.add_argument('--password', default='root')
parser.add_argument('--concurrency', default=20, type=int)
parser.add_argument('--number', default=50, type=int)


if __name__ == '__main__':
    arguments = parser.parse_known_args()[0]

    work_loop = asyncio.new_event_loop()
    work_loop.run_until_complete(setup_container(arguments, work_loop))

    print('Testing writes')
    print('==============')
    tester = LoadTester(WriteLoadTest, arguments)
    tester()
    tester.stats()

    work_loop = asyncio.new_event_loop()
    work_loop.run_until_complete(setup_container(arguments, work_loop))

    print('\n\npopulating site...')
    print('==================')
    tester = LoadTester(BuildContent, arguments)
    tester()

    print('\n\nTesting reads')
    print('=============')
    tester = LoadTester(ReadLoadTest, arguments)
    tester()
    tester.stats()

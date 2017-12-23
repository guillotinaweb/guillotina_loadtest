from aiohttp import web
from glt import conf
from glt import fixtures
from glt import utils
from guillotina.factory import make_app
from guillotina.tests.docker_containers import cockroach_image
from guillotina.tests.docker_containers import postgres_image
from guillotina_rediscache.tests.docker_redis import redis_image
from multiprocessing import Process

import argparse
import asyncio
import json
import logging
import os
import time


logger = logging.getLogger('glt')
parser = argparse.ArgumentParser(description='Load test guillotina')
parser.add_argument('--concurrency', default=20, type=int)
parser.add_argument('--number', default=50, type=int)
parser.add_argument('--transaction-strategy', default='resolve')
parser.add_argument('--db-type', default='postgresql')
parser.add_argument('--cache', action='store_true')
parser.add_argument('--skip-site-creation', action='store_true')


class LoadTester:

    def __init__(self, thread_class, arguments):
        self._thread_class = thread_class
        self._start = 0
        self._end = 0
        self._total_reqs = 0
        self._total_writes = 0
        self._total_updates = 0
        self._total_retries = 0
        self._threads = []
        self._arguments = arguments

    def __call__(self):
        self._start = time.time()

        print(f'starting up {self._arguments.concurrency} threads for '
              f'{self._thread_class.title} test')

        for i in range(self._arguments.concurrency):
            thread = self._thread_class(
                conf.G_URL + '/container', self._arguments.number)
            self._threads.append(thread)
            thread.start()

        print(f'Waiting to finish')

        for thread in self._threads:
            thread.join()
            self._total_reqs += thread._loaded
            self._total_writes += thread._created
            self._total_updates += thread._updated
            self._total_retries += thread._retries

        self._end = time.time()

    def print_stats(self):
        print('\n\n')
        title = f'Test results for: {self._thread_class.title}'
        print(title)
        print('=' * len(title))
        print(f'Total requests: {self._total_reqs}')
        if self._total_writes > 0:
            print(f'Total writes: {self._total_writes}')
        if self._total_updates > 0:
            print(f'Total updates: {self._total_updates}')
        if self._total_retries > 0:
            print(f'Total retries: {self._total_retries}')
        print(f'Seconds: {self._end - self._start}')
        print(f'Per sec: {self._total_reqs / (self._end - self._start)}')
        if self._total_writes > 0:
            print(f'Writes per sec: {self._total_writes / (self._end - self._start)}')  # noqa
        if self._total_updates > 0:
            print(f'Updates per sec: {self._total_updates / (self._end - self._start)}')  # noqa
        if self._total_retries > 0:
            print(f'Retries per sec: {self._total_retries / (self._end - self._start)}')  # noqa
        print('\n\n')

    def dict_stats(self):
        return {
            'writes': self._total_writes,
            'updates': self._total_updates,
            'requests': self._total_reqs,
            'retries': self._total_retries,
            'duration': self._end - self._start
        }


class Environment:
    is_travis = 'TRAVIS' in os.environ

    def __init__(self, arguments):
        self.arguments = arguments
        self.connections = {}

    def setup(self):
        if self.arguments.db_type == 'cockroach':
            self.connections['cockroach'] = cockroach_image.run()
        if self.arguments.cache:
            self.connections['redis'] = redis_image.run()
        if not self.is_travis and self.arguments.db_type == 'postgresql':
            self.connections['postgresql'] = postgres_image.run()
        else:
            self.connections['postgresql'] = 'localhost', 5432

    def teardown(self):
        if self.arguments.db_type == 'cockroach':
            cockroach_image.stop()
        if self.arguments.cache:
            redis_image.stop()
        if self.arguments.db_type == 'postgresql' and not self.is_travis:
            postgres_image.stop()


def run_guillotina(settings):
    web_loop = asyncio.new_event_loop()
    app = make_app(settings=settings, loop=web_loop)
    asyncio.set_event_loop(web_loop)
    web.run_app(app, host=settings.get('host', '0.0.0.0'),
                port=settings.get('address', settings.get('port')),
                loop=web_loop)


def run_tests(configuration, arguments):
    if not arguments.skip_site_creation:
        g_process = Process(target=run_guillotina, args=(configuration.conf,))
        g_process.start()
        time.sleep(5)

    stats = {}

    try:
        work_loop = asyncio.new_event_loop()
        work_loop.run_until_complete(
            utils.setup_container(arguments, work_loop))

        tester = LoadTester(fixtures.WriteLoadTest, arguments)
        tester()
        tester.print_stats()
        stats[fixtures.WriteLoadTest.title.replace(' ', '-').lower()] = tester.dict_stats()  # noqa

        work_loop = asyncio.new_event_loop()
        work_loop.run_until_complete(
            utils.setup_container(arguments, work_loop))

        print('\n\npopulating site...')
        print('==================')
        tester = LoadTester(fixtures.BuildContent, arguments)
        tester()

        tester = LoadTester(fixtures.CrawlLoadTest, arguments)
        tester()
        tester.print_stats()
        stats[fixtures.CrawlLoadTest.title.replace(' ', '-').lower()] = tester.dict_stats()  # noqa

        tester = LoadTester(fixtures.ReadLoadTest, arguments)
        tester()
        tester.print_stats()
        stats[fixtures.ReadLoadTest.title.replace(' ', '-').lower()] = tester.dict_stats()  # noqa

        tester = LoadTester(fixtures.CrawlAndUpdateLoadTest, arguments)
        tester()
        tester.print_stats()
        stats[fixtures.CrawlAndUpdateLoadTest.title.replace(' ', '-').lower()] = tester.dict_stats()  # noqa

        original_concurrency = arguments.concurrency
        original_number = arguments.number
        arguments.concurrency = 5
        arguments.number = 20
        tester = LoadTester(fixtures.ContentiousUpdateLoadTest, arguments)
        tester()
        tester.print_stats()
        stats[fixtures.ContentiousUpdateLoadTest.title.replace(' ', '-').lower()] = tester.dict_stats()  # noqa

        arguments.concurrency = original_concurrency
        arguments.number = original_number
    except:
        logger.error('Error running test:', exc_info=True)

    if not arguments.skip_site_creation:
        g_process.terminate()
        while not g_process.is_alive():
            time.sleep(0.5)
        time.sleep(5)

    return stats


def run():
    arguments = parser.parse_known_args()[0]

    if not arguments.skip_site_creation:
        env = Environment(arguments)
        env.setup()
        configuration = conf.get_configuration(
            env,
            arguments.db_type,
            arguments.transaction_strategy,
            arguments.cache
        )

        filename = '{}-{}-{}.json'.format(
            arguments.db_type, arguments.transaction_strategy,
            arguments.cache and 'cache' or 'nocache'
        )
    else:
        configuration = conf.get_configuration(
            env,
            'unknown',
            'unknown',
            'unknown'
        )
        filename = 'unknown-unknown-unknown.json'

    result = {
        'configuration': configuration.conf,
        'data': run_tests(configuration, arguments)
    }
    if not os.path.exists('output/results'):
        os.mkdir('output/results')
    result_dir = os.path.join(
        'output/results', os.environ.get('TRAVIS_BUILD_NUMBER', '0'))
    if not os.path.exists(result_dir):
        os.mkdir(result_dir)

    fi = open(os.path.join(result_dir, filename), 'w')
    fi.write(json.dumps(result, indent=4, sort_keys=True))
    fi.close()

    if not arguments.skip_site_creation:
        env.teardown()

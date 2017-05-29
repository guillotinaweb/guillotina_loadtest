BASE_CONF = {
    "applications": ["guillotina_rediscache"],
    "databases": [],
    "host": "127.0.0.1",
    "port": 8080,
    "static": [],
    "root_user": {
        "password": "root"
    },
    "cors": {
        "allow_origin": ["*"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "utilities": [],
    "redis": {
        'host': 'localhost',
        'port': 6379,
        'ttl': 3600,
        'memory_cache_size': 1000
    }
}

G_URL = 'http://localhost:8080/db'


class Configuration:

    def __init__(self, db_conf, aspect=None):
        self.db_conf = db_conf
        self.conf = BASE_CONF.copy()
        self.conf['databases'].append({"db": self.db_conf})
        self.aspect = aspect

    @property
    def db_type(self):
        return self.db_conf['storage']

    @property
    def transaction_strategy(self):
        return self.db_conf['transaction_strategy']


PostgresqlConfiguration = {
    "storage": "postgresql",
    "dsn": {
        "scheme": "postgres",
        "dbname": "guillotina",
        "user": "postgres",
        "host": "localhost",
        "password": "",
        "port": 5432
    }
}


CockroachConfiguration = {
    "storage": "cockroach",
    "isolation_level": "snapshot",
    "dsn": "postgresql://root@127.0.0.1:26257/guillotina?sslmode=disable",
    "etcd": {
        "host": "127.0.0.1",
        "port": 2379
    }
}


def get_configuration(db_type, transaction_strategy, cache=False):
    if db_type == 'cockroach':
        db_conf = CockroachConfiguration.copy()
    else:
        db_conf = PostgresqlConfiguration.copy()
    db_conf['transaction_strategy'] = transaction_strategy
    if cache:
        db_conf['cache_strategy'] = 'redis'
    return Configuration(db_conf)
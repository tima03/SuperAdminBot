import re
import psycopg2
from decouple import config
from psycopg2.extras import Json
import json
import logging


class PostgresHandler:
    def __init__(self, db_url=None):
        self.cursor = None
        self.db_url = db_url or config('PG_LINK')
        self.conn = None
        self._parse_database_url()

    def _parse_database_url(self):
        # Регулярное выражение для парсинга строки подключения
        pattern = re.compile(
            r'postgresql://(?P<username>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>[^/]+)/(?P<dbname>.+)'
        )
        match = pattern.match(self.db_url)
        if match:
            self.username = match.group('username')
            self.password = match.group('password')
            self.host = match.group('host')
            self.port = match.group('port')
            self.dbname = match.group('dbname')

    def connect_by_link(self):
        # Подключение к базе данных
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
        except psycopg2.DatabaseError as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False
        return True

    def connect_by_UPHD(self):
        try:
            self.conn = psycopg2.connect(dbname=self.dbname, user=self.username, password=self.password, host=self.host,
                                         port=self.port)
            self.cursor = self.conn.cursor()
        except psycopg2.DatabaseError as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False
        return True

    def disconnect(self):
        # Отключение от базы данных
        if self.cursor:
            self.cursor.close()
        else:
            return False
        if self.conn:
            self.conn.close()
            return True
        else:
            return False
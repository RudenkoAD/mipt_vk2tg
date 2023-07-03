import psycopg2
from psycopg2.extras import DictCursor
from config import psql_config
from classes import Link, User
import logging

log = logging.getLogger(__name__)

class sqlcrawler:
    def __init__(self) -> None:
        self.conn = psycopg2.connect(dbname=psql_config.dbname, user=psql_config.user, 
                        password=psql_config.password, host=psql_config.host)
        self.conn.autocommit=True
        self.cursor = self.conn.cursor(cursor_factory=DictCursor)

    def is_subscribed(self, user_id, group_name):
      self.cursor.execute(f"SELECT active from links where group_name = {group_name} AND user_id = {user_id}")
      ans = self.cursor.fetchone()
      if ans is None:
         ans = False
      return ans

    def flip_subscribe(self, user_id, group_name):
      sub = self.is_subscribed(user_id, group_name)
      self.cursor.execute(f"UPDATE links SET active = {not sub}")

    def get_subscribers(self, group_name):
      self.cursor.execute(f"SELECT user_id from links where group_name = {group_name} AND active = True")
      ans = self.cursor.fetchall()
      return ans

    def __del__(self):
        self.cursor.close()
        self.conn.close()
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
        self.conn.autocommit = True
        self.cursor = self.conn.cursor(cursor_factory=DictCursor)

    def get_post_id(self, group_id):
        self.cursor.execute(
            f"SELECT post_id from groups where group_id = {group_id}")
        post_id = self.cursor.fetchone()
        if post_id:
            return post_id["post_id"]
        else:
            return None

    def update_post_id(self, group_id, post_id):
        self.cursor.execute(
            f"UPDATE groups SET post_id = {post_id} WHERE group_id = {group_id}")

    def is_subscribed(self, user_id, group_name):
        group_id = self.get_group_id_by_name(group_name)
        self.cursor.execute(
            f"SELECT active from links where group_id = {group_id} AND user_id = {user_id}")
        ans = self.cursor.fetchone()
        if ans is None:
            return False
        return ans["active"]

    def get_group_id_by_name(self, group_name):
        requeststring = f"SELECT group_id from groups where group_name = '{group_name}'"
        self.cursor.execute(requeststring)
        ans = self.cursor.fetchone()
        if ans:
            return ans["group_id"]
        else:
            return ans
    
    def get_parent(self, folder_name):
        self.cursor.execute(
            f"SELECT parent_name from folders where folder_name = '{folder_name}'")
        ans = self.cursor.fetchone()
        if ans:
            return ans["parent_name"]
        else:
            return ans

    def get_group_name_by_id(self, group_id):
        self.cursor.execute(
            f"SELECT group_name from groups where group_id = '{group_id}'")
        ans = self.cursor.fetchone()
        if ans:
            return ans["group_name"]
        else:
            return ans

    def get_groups(self):
        '''
        returns a list of [group_id, group_name, group_link]
        '''
        self.cursor.execute("SELECT group_id, group_name, group_link from groups")
        ans = self.cursor.fetchall()
        return ans

    def get_groups_from_folder(self, folder):
        '''
        returns a list of [group_id, group_name, group_link]
        '''
        self.cursor.execute(
            f"SELECT group_id, group_name, group_link from groups where folder = '{folder}'")
        ans = self.cursor.fetchall()
        return ans

    def get_folders(self, parent = None):
        if parent is None:
            self.cursor.execute(f"SELECT folder_id, folder_name from folders where parent_name is NULL")
        else:
            self.cursor.execute(f"SELECT folder_id, folder_name from folders where parent_name = '{parent}'")
        ans = self.cursor.fetchall()
        return ans

    def flip_subscribe(self, user_id, group_name):
        group_id = self.get_group_id_by_name(group_name)
        self.cursor.execute(
            f"SELECT * from links WHERE group_id = {group_id} AND user_id = {user_id}")
        data = self.cursor.fetchone()
        if data:
            self.cursor.execute(
                f"UPDATE links SET active = {not data['active']} WHERE group_id = {group_id} AND user_id = {user_id}")
        else:
            self.cursor.execute(
                f"INSERT into links (user_id, group_id, active) VALUES ({user_id}, {group_id}, {True})")

    def get_subscribers(self, group_id):
        self.cursor.execute(
            f"SELECT user_id from links where group_id = {group_id} AND active = True")
        ans = self.cursor.fetchall()
        return [data[0] for data in ans]

    def __del__(self):
        self.cursor.close()
        self.conn.close()

import psycopg2  #upm package(psycopg2-binary)
from psycopg2.extras import DictCursor  #upm package(psycopg2-binary)
from bot.secrets import psql_config
from bot.logger import setup_logger

logger = setup_logger("sql")


class sqlcrawler:

  def __init__(self) -> None:
    self.conn = psycopg2.connect(dbname=psql_config.dbname,
                                 user=psql_config.user,
                                 password=psql_config.password,
                                 host=psql_config.host)
    self.conn.autocommit = True
    self.cursor = self.conn.cursor(cursor_factory=DictCursor)

  def reconnect(self):
    self.conn = psycopg2.connect(dbname=psql_config.dbname,
                                 user=psql_config.user,
                                 password=psql_config.password,
                                 host=psql_config.host)
    self.conn.autocommit = True
    self.cursor = self.conn.cursor(cursor_factory=DictCursor)
    logger.debug("reconnected to database")

  def execute(self, string):
    finished = False
    while not finished:
      try:
        self.cursor.execute(string)
        finished = True
      except:
        self.reconnect()

  def get_post_id(self, group_id):
    self.execute(f"SELECT post_id from groups where group_id = {group_id}")
    post_id = self.cursor.fetchone()
    try:
      return post_id["post_id"]
    except:
      return None

  def update_post_id(self, group_id, post_id):
    self.execute(
      f"UPDATE groups SET post_id = {post_id} WHERE group_id = {group_id}")

  def is_subscribed(self, user_id, group_name):
    group_id = self.get_group_id_by_name(group_name)
    self.execute(
      f"SELECT active from links where group_id = {group_id} AND user_id = {user_id}"
    )
    ans = self.cursor.fetchone()
    if ans is None:
      return False
    return ans["active"]

  def get_group_id_by_name(self, group_name):
    requeststring = f"SELECT group_id from groups where group_name = '{group_name}'"
    self.execute(requeststring)
    ans = self.cursor.fetchone()
    if ans:
      return ans["group_id"]
    else:
      return ans

  def get_parent(self, folder_name):
    self.execute(
      f"SELECT parent_name from folders where folder_name = '{folder_name}'")
    ans = self.cursor.fetchone()
    if ans:
      return ans["parent_name"]
    else:
      return ans

  def get_group_name_by_id(self, group_id):
    self.execute(
      f"SELECT group_name from groups where group_id = '{group_id}'")
    ans = self.cursor.fetchone()
    if ans:
      return ans["group_name"]
    else:
      return ans

  def get_folder_name_by_id(self, folder_id):
    self.execute(
      f"SELECT folder_name from folders where folder_id = '{folder_id}'")
    ans = self.cursor.fetchone()
    if ans:
      return ans["folder_name"]
    else:
      return ans

  def get_folder_id_by_name(self, folder_name):
    self.execute(
      f"SELECT folder_id from folders where folder_name = '{folder_name}'")
    ans = self.cursor.fetchone()
    if ans:
      return ans["folder_id"]
    else:
      return ans

  def get_groups(self):
    '''
        returns a list of [group_id, group_name, group_link]
        '''
    self.execute(
      "SELECT group_id, group_name, group_link from groups ORDER BY group_name ASC"
    )
    ans = self.cursor.fetchall()
    return ans

  def get_groups_from_folder(self, folder):
    '''
        returns a list of [group_id, group_name, group_link]
        '''
    self.execute(
      f"SELECT group_id, group_name, group_link from groups where folder = '{folder}' ORDER BY group_name ASC"
    )
    ans = self.cursor.fetchall()
    return ans

  def get_folders(self, parent=None):
    if parent is None:
      self.execute(
        f"SELECT folder_id, folder_name from folders where parent_name is NULL ORDER BY folder_name ASC"
      )
    else:
      self.execute(
        f"SELECT folder_id, folder_name from folders where parent_name = '{parent}' ORDER BY folder_name ASC"
      )
    ans = self.cursor.fetchall()
    return ans

  def flip_subscribe(self, user_id, group_id):
    self.execute(
      f"SELECT * from links WHERE group_id = {group_id} AND user_id = {user_id}"
    )
    data = self.cursor.fetchone()
    if data:
      self.execute(
        f"UPDATE links SET active = {not data['active']} WHERE group_id = {group_id} AND user_id = {user_id}"
      )
    else:
      self.execute(
        f"INSERT into links (user_id, group_id, active) VALUES ({user_id}, {group_id}, {True})"
      )

  def get_subscribers(self, group_id):
    self.execute(
      f"SELECT user_id from links where group_id = {group_id} AND active = True"
    )
    ans = self.cursor.fetchall()
    return [data[0] for data in ans]

  def __del__(self):
    self.cursor.close()
    self.conn.close()

import sqlite3
from classes import QueueMessage, Group, Folder, Link
class sqlcrawler:

    def __init__(self, db_path="database.sqlite"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def execute(self, string, values=None):
        try:
            if values:
                self.cursor.execute(string, values)
            else:
                self.cursor.execute(string)
            self.conn.commit()
        except sqlite3.Error as e:
            print("SQLite error:", e)

    def get_group_by_name(self, group_name):
        self.execute("SELECT * FROM groups WHERE group_name = ?", (group_name,))
        ans = self.cursor.fetchone()
        return Group(*ans) if ans else None

    def insert_group(self, group_name, group_id, folder, post_id=None):
        self.execute("INSERT INTO groups (group_name, group_id, group_link, folder) VALUES (?, ?, ?, ?)", (group_name, group_id, folder, post_id))
    
    def insert_folder(self, folder_name, parent_name=None):
        self.execute("INSERT INTO folders (folder_name, parent_name) VALUES (?, ?)", (folder_name, parent_name))

    def get_all_user_ids(self):
        self.execute("SELECT DISTINCT user_id FROM links WHERE active = ?", (True,))
        users = self.cursor.fetchall()
        return [user[0] for user in users]

    def get_group_by_id(self, group_id):
        self.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,))
        ans = self.cursor.fetchone()
        return Group(*ans) if ans else None

    def get_folder_by_id(self, folder_id):
        self.execute("SELECT * FROM folders WHERE folder_id = ?", (folder_id,))
        ans = self.cursor.fetchone()
        return Folder(*ans) if ans else None

    def get_folder_by_name(self, folder_name):
        self.execute("SELECT * FROM folders WHERE folder_name = ?", (folder_name,))
        ans = self.cursor.fetchone()
        return Folder(*ans) if ans else None

    def get_groups(self):
        self.execute("SELECT * FROM groups ORDER BY group_name ASC")
        ans = self.cursor.fetchall()
        return [Group(*x) for x in ans]

    def get_groups_from_folder_name(self, folder):
        self.execute("SELECT * FROM groups WHERE folder = ? ORDER BY group_name ASC", (folder,))
        ans = self.cursor.fetchall()
        return [Group(*x) for x in ans]
    
    def search_groups(self, subname):
      if subname.startswith("http"):
        stripped = subname.split("/")[-1]
        self.execute("SELECT * FROM groups WHERE group_link LIKE ? ORDER BY group_name ASC", (f"%{stripped}%",))
      else:
        self.execute("SELECT * FROM groups WHERE group_name LIKE ? ORDER BY group_name ASC", (f"%{subname}%",))
      ans = self.cursor.fetchmany(5)
      return [Group(*x) for x in ans]

    def get_folders(self, parent_name=None):
        if parent_name is None:
            self.execute("SELECT * FROM folders WHERE parent_name IS NULL ORDER BY folder_name ASC")
        else:
            self.execute("SELECT * FROM folders WHERE parent_name = ? ORDER BY folder_name ASC", (parent_name,))
        ans = self.cursor.fetchall()
        return [Folder(*x) for x in ans]

    def get_subscribers(self, group_id):
        self.execute("SELECT user_id FROM links WHERE group_id = ? AND active > ?", (group_id, 0))
        ans = self.cursor.fetchall()
        return [data[0] for data in ans]

    def subscription_status(self, user_id, group_id):
        if group_id is not None:
            self.execute("SELECT active FROM links WHERE group_id = ? AND user_id = ?", (group_id, user_id))
            ans = self.cursor.fetchone()
            return int(ans[0]) if ans else 0
        return 0

    def get_message_from_queue(self):
        self.execute("SELECT * FROM queue LIMIT 1")
        message = self.cursor.fetchone()
        return QueueMessage(*message) if message else None

    def del_message_from_queue(self, message_id):
        self.execute("DELETE FROM queue WHERE message_id = ?", (message_id,))
        message = self.cursor.fetchone()
        return message if message else None

    def put_message_into_queue(self, chat_id, caption, media:str=None, notifications:int=1):
        self.execute(f"INSERT INTO queue (chat_id, caption, media, notifications) VALUES (?, ?, ?, ?)", (chat_id, caption, media, notifications))

    def update_post_id(self, group_id, post_id):
        self.execute("UPDATE groups SET post_id = ? WHERE group_id = ?", (post_id, group_id))

    def remove_user(self, user_id):
        self.execute("DELETE FROM links WHERE user_id = ?", (user_id,))
        self.execute("DELETE FROM queue WHERE chat_id = ?", (user_id,))

    def delete_queue(self):
        self.execute("DELETE FROM queue")

    def change_subscribe(self, user_id, group_id):
      self.execute("SELECT * FROM links WHERE group_id = ? AND user_id = ?", (group_id, user_id))
      data = self.cursor.fetchone()
      if data:
        #cycle between 0, 1, and 2
        new_data = (data[2] + 1) % 3
        self.execute("UPDATE links SET active = ? WHERE group_id = ? AND user_id = ?", (new_data, group_id, user_id))
      else:
        self.execute("INSERT INTO links (user_id, group_id, active) VALUES (?, ?, ?)", (user_id, group_id, 1))

    def __del__(self):
        self.cursor.close()
        self.conn.close()

# Usage:
import json
if __name__ == "__main__":
    db_path = 'database.sqlite'
    crawler = sqlcrawler(db_path)
    print(crawler.search_groups("https://vk.com/128"))

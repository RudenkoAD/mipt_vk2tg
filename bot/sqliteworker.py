import sqlite3
from classes import QueueMessage, Group, Folder
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

    # ... Implement your other methods similarly ...

    def get_group_by_name(self, group_name):
        self.execute("SELECT * FROM groups WHERE group_name = ?", (group_name,))
        ans = self.cursor.fetchone()
        return Group(*ans) if ans else None

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

    def get_folders(self, parent_name=None):
        if parent_name is None:
            self.execute("SELECT * FROM folders WHERE parent_name IS NULL ORDER BY folder_name ASC")
        else:
            self.execute("SELECT * FROM folders WHERE parent_name = ? ORDER BY folder_name ASC", (parent_name,))
        ans = self.cursor.fetchall()
        return [Folder(*x) for x in ans]

    def get_subscribers(self, group_id):
        self.execute("SELECT user_id FROM links WHERE group_id = ? AND active = ?", (group_id, True))
        ans = self.cursor.fetchall()
        return [data[0] for data in ans]

    def is_subscribed(self, user_id, group_id):
        if group_id is not None:
            self.execute("SELECT active FROM links WHERE group_id = ? AND user_id = ?", (group_id, user_id))
            ans = self.cursor.fetchone()
            return ans[0] if ans else False
        return False

    def get_message_from_queue(self):
        self.execute("SELECT * FROM queue LIMIT 1")
        message = self.cursor.fetchone()
        return QueueMessage(*message) if message else None

    def del_message_from_queue(self, message_id):
        self.execute("DELETE FROM queue WHERE message_id = ?", (message_id,))
        message = self.cursor.fetchone()
        return message if message else None

    def put_message_into_queue(self, chat_id, caption, media:str=None):
        self.execute(f"INSERT INTO queue (chat_id, caption, media) VALUES (?, ?, ?)", (chat_id, caption, media))

    def update_post_id(self, group_id, post_id):
        self.execute("UPDATE groups SET post_id = ? WHERE group_id = ?", (post_id, group_id))

    def delete_user(self, user_id):
        self.execute("DELETE FROM links WHERE user_id = ?", (user_id,))
        # Add a corresponding deletion in any other relevant tables
        # e.g., if there are more tables with user references.

    def delete_queue(self):
        self.execute("DELETE FROM queue")


    def flip_subscribe(self, user_id, group_id):
        self.execute("SELECT * FROM links WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        data = self.cursor.fetchone()
        if data:
            self.execute("UPDATE links SET active = ? WHERE group_id = ? AND user_id = ?", (not data[2], group_id, user_id))
        else:
            self.execute("INSERT INTO links (user_id, group_id, active) VALUES (?, ?, ?)", (user_id, group_id, True))
    
    def __del__(self):
        self.cursor.close()
        self.conn.close()

# Usage:
import json
if __name__ == "__main__":
    db_path = 'database.sqlite'  # Provide the path to your SQLite database file
    crawler = sqlcrawler(db_path)
    confirm = input("are you sure you wanna delete queue?")
    if confirm == "yes":
        crawler.delete_queue()

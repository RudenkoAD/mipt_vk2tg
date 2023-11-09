from dataclasses import dataclass

@dataclass
class Group:
    group_id: int
    group_name: str
    post_id: int
    group_link: str
    folder: str

@dataclass
class Folder:
    folder_id: int
    folder_name: str
    parent_name: str = None
    folder_text: str = None

@dataclass
class Link:
    user_id: int
    group_id: int
    active: int #0 if not subscribed, 1 if subscribed with notifications, 2 if subscribed without notifications

@dataclass
class QueueMessage:
    message_id: int
    chat_id: int
    caption: str
    media: str = None
    notifications: int = 1
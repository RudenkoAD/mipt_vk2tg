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
    active: bool

@dataclass
class QueueMessage:
    message_id: int
    chat_id: int
    caption: str
    media: str = None

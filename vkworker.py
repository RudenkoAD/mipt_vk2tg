import vk
import logging
import os
import json
from config import vk_config
from sqlworker import sqlcrawler
from classes import Link, User

log = logging.getLogger(__name__)

def exist_bigger_element(list_: list[int], element: int):
    """Returns true if in list_ exists element bigger than element"""
    for list_el in list_:
        if list_el > element:
            return True
    return False

def get_photos_links(attachments: list[dict]) -> list[str] | None:
    """:param attachments: VK api response - list of dicts. Each dict is attachment.
    :return: list of photos links or None if there is no photos"""
    if attachments is None or len(attachments) == 0:
        return None
    return [attachment["photo"]["sizes"][-1]["url"] for attachment in attachments if attachment["type"] == "photo"]

class vkfetcher:
  def __init__(self, link:Link = None, vk_token: str = vk_config.access_token, dbmanager=sqlcrawler()):
        self.link: Link = link
        self.api: vk.API = vk.API(vk_token, v="5.131")
        self.dbmanager = dbmanager
        self.last_api_call_time: int = 0
        if self.link.post_id is None:
            self.link.post_id = max([p["id"] for p in self.api.wall.get(owner_id=self.link.vk_id, count=2)["items"]])
        self.dbmanager.update_post(self.link)

  def get_new_posts(self, link = None, iteration_limit=20, do_db = True):
        if link is None:
            link = self.link
        posts = []
        for i in range(iteration_limit):
            new_posts = self.api.wall.get(owner_id=self.link.vk_id, count=5, offset=5*i)["items"]
            new_posts_ids = [post["id"] for post in new_posts]
            posts += new_posts
            if not exist_bigger_element(new_posts_ids, self.link.post_id):
                log.debug(posts)
                posts = [p for p in posts if p["id"] > self.link.post_id]
                if len(posts) != 0:
                    self.link.post_id = posts[0]["id"]
                    log.info(f"New last post id for {self.link.vk_id} is {self.link.post_id}")
                else:
                    log.info("No new posts found")
                if do_db:
                    self.dbmanager.update_post(self.link)
                return posts
        log.error("Too many posts found for {self.vk_id}. Maybe something wrong")
        raise ValueError("Too many posts found")

if __name__ == "__main__":
    vk_page_id = -214737987  # Replace with the VK page ID you want to check
    access_token = vk_config.access_token# Replace with your VK access token

    crawler = vkfetcher(Link(vk_page_id, None, None, None), access_token)
    new_posts = crawler.get_new_posts()
    if new_posts:
        print(f"Found {len(new_posts)} new posts:")
        for post in new_posts:
            print(f"- {post['text']}")
            print("\n\n")
    else:
        print("No new posts found or an error occurred.")

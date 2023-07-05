import vk
import logging
import os
import json
from config import vk_config
from sqlworker import sqlcrawler

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
  def __init__(self, vk_token: str = vk_config.access_token, dbmanager=sqlcrawler()):
        self.api: vk.API = vk.API(vk_token, v="5.131")
        self.dbmanager = dbmanager

  def get_new_posts(self, vk_id, iteration_limit=20):
        posts = []
        post_id = self.dbmanager.get_post_id(vk_id)
        if post_id is None:
            try:
                post_id = max([p["id"] for p in self.api.wall.get(owner_id=vk_id, count=2)["items"]])
            except:
                raise ValueError(f"Something is off with group_id = {vk_id}")
        for i in range(iteration_limit):
            new_posts = self.api.wall.get(owner_id=vk_id, count=5, offset=5*i)["items"]
            new_posts_ids = [post["id"] for post in new_posts]
            posts += new_posts
            if not exist_bigger_element(new_posts_ids, post_id):
                log.debug(posts)
                posts = [p for p in posts if p["id"] > post_id]
                if len(posts) != 0:
                    post_id = posts[0]["id"]
                    log.info(f"New last post id for {vk_id} is {post_id}")
                else:
                    log.info("No new posts found")
                self.dbmanager.update_post_id(vk_id, post_id)
                return posts
        log.error("Too many posts found for {self.vk_id}. Maybe something wrong")
        raise ValueError("Too many posts found")

if __name__ == "__main__":
    vk_page_id = -214737987  # Replace with the VK page ID you want to check
    access_token = vk_config.access_token# Replace with your VK access token

    crawler = vkfetcher(access_token)
    new_posts = crawler.get_new_posts(-214737987)
    if new_posts:
        print(f"Found {len(new_posts)} new posts:")
        for post in new_posts:
            print(f"- {post['text']}")
            print("\n\n")
    else:
        print("No new posts found or an error occurred.")

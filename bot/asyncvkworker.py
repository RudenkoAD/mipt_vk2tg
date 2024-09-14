from vkbottle import VKAPIError
from vkbottle.api import API
import asyncio
from secrets import VK_ACCESS_TOKEN
from sqliteworker import sqlcrawler
from logger import setup_logger

log = setup_logger("vk")

def exist_bigger_element(list_, element):
    """Returns true if in list_ exists element bigger than element"""
    return any(list_el > element for list_el in list_ if list_el is not None)


class VkFetcher:
    
    def __init__(self, vk_token: str = VK_ACCESS_TOKEN, dbmanager=None):
        self.api = API(vk_token)
        self.dbmanager = dbmanager or sqlcrawler()  # Avoid mutable default arguments
    
    async def get_new_posts(self, vk_id, iteration_limit=20):
        posts = []
        group = self.dbmanager.get_group_by_id(vk_id)
        post_id = group.post_id
        POST_COUNT = 10
        if post_id is None:
          try:
              response = await self.api.wall.get(owner_id=vk_id, count=POST_COUNT)
              post_id = max([p.id for p in response.items])
              self.dbmanager.update_post_id(group.group_id, post_id)
          except VKAPIError as e:
              log.error(f"Couldn't get new post id for group_id = {vk_id}. Error: {e}")
              if post_id is None:
                  raise ValueError(f"Couldn't get new post id for group_id = {vk_id}")

        unique_ids = set()
        unique_posts = []
        for i in range(iteration_limit):
            response = await self.api.wall.get(owner_id=vk_id, count=POST_COUNT, offset=POST_COUNT*i)
            new_posts = response.items
            new_posts_ids = [post.id for post in new_posts]
            posts.extend(new_posts)
            if not exist_bigger_element(new_posts_ids, post_id):
                posts = [p for p in posts if p.id > post_id]
                log.debug(f"{'Found' if len(posts) != 0 else 'No'} new posts found for {vk_id}")
                for post in posts:
                    if post.id in unique_ids:
                        continue
                    else:
                        unique_ids.add(post.id)
                        unique_posts.append(post)
                return unique_posts


        log.error(f"Too many posts found for {vk_id}. Maybe something is wrong")
        raise ValueError(f"Too many posts found for {vk_id}")

    async def get_post_by_id(self, vk_id, post_id):
        for i in range(20):
            try:
                response = await self.api.wall.get(owner_id=vk_id, count=5, offset=5*i)
                new_posts = response.items
                for post in new_posts:
                    if post.id == post_id:
                        return post
            except Exception as e:
                log.error(f"Error fetching posts for vk_id: {vk_id} with error: {e}")
        return None



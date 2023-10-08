from vkbottle.api import API
import asyncio
from secrets import VK_ACCESS_TOKEN
from sqliteworker import sqlcrawler
from logger import setup_logger

log = setup_logger("vk")

async def exist_bigger_element(list_, element):
    """Returns true if in list_ exists element bigger than element"""
    for list_el in list_:
        if list_el > element:
            return True
    return False

class VkFetcher:

    def __init__(self, vk_token: str = VK_ACCESS_TOKEN, dbmanager=sqlcrawler()):
        self.api = API(vk_token)
        self.dbmanager = dbmanager  # Предположим, что ваш класс для работы с БД называется YourDbManager

    async def get_new_posts(self, vk_id, iteration_limit=20):
        posts = []
        post_id = self.dbmanager.get_group_by_id(vk_id).post_id
        if post_id is None:
            try:
                response = await self.api.wall.get(owner_id=vk_id, count=2)
                post_id = max([p.id for p in response.items])
            except Exception:
                log.error(f"couldn't get a new post_id (instead of NULL) for group_id = {vk_id}")
                raise ValueError(f"couldn't get a new post_id (instead of NULL) for group_id = {vk_id}")

        for i in range(iteration_limit):
            response = await self.api.wall.get(owner_id=vk_id, count=1, offset=i)
            new_posts = response.items
            new_posts_ids = [post.id for post in new_posts]
            posts.extend(new_posts)
            if not await exist_bigger_element(new_posts_ids, post_id):
                posts = [p for p in posts if p.id > post_id]
                log.debug(f"Found new posts for {vk_id}" if len(posts) != 0 else f"No new posts found for {vk_id}")
                unique_ids = []
                unique_posts = []
                for post in posts:
                    if post.id in unique_ids:
                        continue
                    else:
                        unique_ids.append(post.id)
                        unique_posts.append(post)
                return unique_posts
              
              

        log.error(f"Too many posts found for {vk_id}. Maybe something is wrong")
        raise ValueError("Too many posts found")

    async def get_post_by_id(self, vk_id, post_id):
        for i in range(20):
            response = await self.api.wall.get(owner_id=vk_id, count=2, offset=2*i)
            new_posts = response.items
            for post in new_posts:
                if post.id == post_id:
                    return post
        return None

if __name__ == "__main__":
    vk_fetcher = VkFetcher()
    import logging
    logging.getLogger("vkbottle").setLevel(logging.ERROR)
    access_token = VK_ACCESS_TOKEN  # Replace with your VK access token
    post = asyncio.run(vk_fetcher.get_post_by_id(-197752978, 356))
    print(post)


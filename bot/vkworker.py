import vk
from secrets import VK_ACCESS_TOKEN
from sqliteworker import sqlcrawler
from logger import setup_logger

log = setup_logger("vk")


def exist_bigger_element(list_, element):
  """Returns true if in list_ exists element bigger than element"""
  for list_el in list_:
    if list_el > element:
      return True
  return False


class vkfetcher:

  def __init__(self, vk_token: str = VK_ACCESS_TOKEN, dbmanager=sqlcrawler()):
    self.api: vk.API = vk.API(vk_token, v="5.141")
    self.dbmanager = dbmanager

  def get_new_posts(self, vk_id, iteration_limit=20):
    posts = []
    post_id = self.dbmanager.get_post_id(vk_id)
    if post_id is None:
      try:
        post_id = max([
          p["id"] for p in self.api.wall.get(owner_id=vk_id, count=2)["items"]
        ])-1
      except:
        raise ValueError(f"Something is off with group_id = {vk_id}")
    for i in range(iteration_limit):
      new_posts = self.api.wall.get(owner_id=vk_id, count=5,
                                    offset=5 * i)["items"]
      new_posts_ids = [post["id"] for post in new_posts]
      posts += new_posts
      if not exist_bigger_element(new_posts_ids, post_id):#дошли до последнего нового поста, в очередном батче новых нету
        posts = [p for p in posts if p["id"] > post_id]
        log.info(f"found new posts for {vk_id}" if len(posts)!=0 else f"No new posts found for {vk_id}")
        return posts
    log.error(f"Too many posts found for {vk_id}. Maybe something wrong")
    raise ValueError("Too many posts found")

  def get_post_by_id(self, vk_id, post_id):
    for i in range(20):
      new_posts = self.api.wall.get(owner_id=vk_id, count=5,
                                    offset=5 * i)["items"]
      for post in new_posts:
        if post["id"]==post_id: return post
        print(f"id is not {post['id']}")
    return None
  
  def get_video(self, owner_id, video_id, access_key = None):
    return self.api.video.get(owner_id = owner_id, video_id = video_id, access_key = access_key)
  
if __name__ == "__main__":
  import json
  from os import path
  access_token = VK_ACCESS_TOKEN  # Replace with your VK access token
  crawler = vkfetcher(access_token)
  post = crawler.get_post_by_id(-214681464, 155)
  json.dump(obj = post, fp = open("post.json", 'w'))
  # video = crawler.get_video(-173800849, 456239734, access_key = "5ce9c190d2b1ff2775")
  # json.dump(obj = video, fp = open("video.json", 'w'))
  # if new_posts:
  #   print(f"Found {len(new_posts)} new posts:")
  #   for post in new_posts:
  #     print(f"- {post['text']}")
  #     print("\n\n")
  # else:
  #   print("No new posts found or an error occurred.")
  

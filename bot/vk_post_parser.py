import re
from html import escape

from logger import setup_logger

logger = setup_logger("vk_post_parser")

def get_post_link(post_id: int, group_id: int):
  """Returns link to post in VK"""
  link = f"https://vk.com/wall{group_id}_{post_id}"
  return link

def get_group_link(group_id: int):
  """Returns link to post in VK"""
  link = f"https://vk.com/club{-group_id}"
  return link


def get_video_link(attachment):
  if attachment["type"] != "video":
    return None
  return f"https://vk.com/video{attachment['video']['owner_id']}_{attachment['video']['id']}"

def get_photo_link(attachment):
  if attachment["type"] != "photo":
    return None
  return max(attachment['photo']['sizes'], key=lambda x: x['width'])['url']

def get_attachments_links(attachments):
  """:param attachments: VK api response - list of dicts. Each dict is attachment.
    :return: list of photos links or None if there is no photos"""
  if attachments is None or len(attachments) == 0:
    logger.debug("found no photos in attachments")
    return None
  photos_links = [
    get_photo_link(attachment)
    for attachment in attachments
    if attachment["type"] == "photo"
  ]
  # videos_links = [
  #   get_video_link(attachment)
  #   for attachment in attachments
  #   if (attachment.get("type", None) == "video") and (attachment.get("video", {}).get("platform", None) is None)
  # ]
  #print(photos_links, videos_links)
  return photos_links# + videos_links

def wrap_message_text(text, post, group_name, begin:bool, end: bool):
  from_group_text =f'От <a href="{get_group_link(post["owner_id"])}">{group_name}</a>:' 
  post_link_text = f'<a href="{get_post_link(post["id"], post["owner_id"])}">Оригинальный пост</a>'
  final_text = ""
  if begin: final_text+=f"{from_group_text}\n"
  final_text+= text
  if end: final_text+=f"\n{post_link_text}"
  return final_text

def get_message_texts(group_name, post: dict, has_attachments: bool):
  """Returns text message to telegram channel
    :param post: VK api response    """
  CAPTION_LEN = 900
  POST_LEN = 3900
  if len(post["text"])<=(CAPTION_LEN if has_attachments else POST_LEN):
    text = parse_vk_post_text(post["text"])
    text = wrap_message_text(text, post, group_name, begin = True, end=True)
    return [text]
  logger.debug(f"post text was too long, cutting it")
  text_list = []
  split = CAPTION_LEN + post["text"][CAPTION_LEN:].find(" ")
  text = parse_vk_post_text(post["text"][:split])
  text = wrap_message_text(text, post, group_name, begin = True, end=False)
  text_list.append(text)
  N = (len(post["text"])-split)//POST_LEN + 1
  for i in range(N):
    end = True if i==N-1 else False
    text = parse_vk_post_text(post["text"][split+POST_LEN*i:split+POST_LEN*(i+1)])
    text = wrap_message_text(text, post, group_name, False, end)
    text_list.append(text)
  return text_list

def parse_vk_post_text(post_text):
    # Regular expression to match VK embeds (both "id", "club", and standard links)
    embed_pattern = r'\[(id|club)(\d+)\|([^\]]+)\]|\[([^|\]]+)\|([^]]+)\]'

    def replace_embed(match):
        if match.group(1) is not None:  # "id" or "club" format
            embed_type = match.group(1)
            entity_id = match.group(2)
            display_name = escape(match.group(3))

            if embed_type == 'id':
                vk_link = f'<a href="https://vk.com/id{entity_id}">{display_name}</a>'
            elif embed_type == 'club':
                vk_link = f'<a href="https://vk.com/club{entity_id}">{display_name}</a>'
        else:  # Standard link format
            entity_id = match.group(4)
            display_name = escape(match.group(5))
            vk_link = f'<a href="{entity_id}">{display_name}</a>'

        return vk_link

    return re.sub(embed_pattern, replace_embed, post_text)

# Example usage:
if __name__ == "__main__":
  vk_post_text = "Check out [id123|John] and [club456|My Club] on VK. Also, visit [https://example.com|our website]."
  parsed_text = parse_vk_post_text(vk_post_text)
  print(parsed_text)
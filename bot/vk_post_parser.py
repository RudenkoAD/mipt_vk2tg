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


def get_photos_links(attachments):
  """:param attachments: VK api response - list of dicts. Each dict is attachment.
    :return: list of photos links or None if there is no photos"""
  if attachments is None or len(attachments) == 0:
    logger.debug("found no photos in attachments")
    return None
  return [
    max(attachment['photo']['sizes'], key=lambda x: x['width'])['url']
    for attachment in attachments
    if attachment["type"] == "photo"
  ]

def wrap_message_text(text, post, group_name, it, max_it):
  from_group_text =f'От <a href="{get_group_link(post["owner_id"])}">{group_name}</a>:' 
  post_link_text = f'<a href="{get_post_link(post["id"], post["owner_id"])}">Оригинальный пост</a>'
  if(it==1 and max_it==1):
    return f"{from_group_text}\n{text}\n{post_link_text}"
  else:
    return f"{from_group_text}\n{text}...\nчасть {it} из {max_it}\n{post_link_text}"


def get_message_texts(group_name, post: dict):
  """Returns text message to telegram channel
    :param post: VK api response    """
  CAPTION_LEN = 900
  max_it = len(post["text"])//CAPTION_LEN + 1
  if max_it>1:
    logger.info(f"post text was too long, cutting it into {max_it} parts")
  text_list = []
  for it in range(1, max_it+1):
    text = parse_vk_post_text(post["text"][CAPTION_LEN*(it-1):CAPTION_LEN*(it)])
    text = wrap_message_text(text, post, group_name, it, max_it)
    text_list.append(text)
  return text_list

def parse_vk_post_text(post_text):
    # Regular expression to match VK embeds (both "id" and "club")
    embed_pattern = r'\[(id|club)(\d+)\|([^\]]+)\]'

    def replace_embed(match):
        embed_type = match.group(1)
        entity_id = match.group(2)
        display_name = escape(match.group(3))
        
        if embed_type == 'id':
            vk_link = f'<a href="https://vk.com/id{entity_id}">{display_name}</a>'
        elif embed_type == 'club':
            vk_link = f'<a href="https://vk.com/club{entity_id}">{display_name}</a>'
        else:
            vk_link = match.group(0)  # Return the original text if neither "id" nor "club"
        
        return vk_link

    # Replace VK embeds with Telegram-compatible HTML hyperlinks
    parsed_text = re.sub(embed_pattern, replace_embed, post_text)

    return parsed_text

# Example usage:
if __name__ == "__main__":
  vk_post_text = """Приветствуем нового старосту третьекурсников — [id426956952|Савву Савенкова]! 
  Напомним, что староста курса — это тот, кто представляет интересы всего потока. Теперь Савва доступен для решения любых организационных, но не только, вопросов. Он следит за работой старост всех групп и передает информацию от преподавателей.
  Желаем успехов Савве!"""
  parsed_text = parse_vk_post_text(vk_post_text)
  print(parsed_text)
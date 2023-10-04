import re
from html import escape
from logger import setup_logger
from text_storage import TextStorage
logger = setup_logger("vk_post_parser")
from attachmentmanager import Attachment
def get_post_link(post_id: int, group_id: int):
  """Returns link to post in VK"""
  link = f"https://vk.com/wall{group_id}_{post_id}"
  return link

def get_group_link(group_id: int):
  """Returns link to post in VK"""
  link = f"https://vk.com/club{-group_id}"
  return link

def wrap_message_text(text, post, group_name, begin:bool, end: bool, attachments=[]):
  unattached=0
  for attachment in attachments:
    if attachment.attachment_type == "не определили":
      unattached +=1
  
  from_group_text =f'От <a href="{get_group_link(post.owner_id)}">{group_name}</a>:' 
  post_link_text = f'<a href="{get_post_link(post.id, post.owner_id)}">Оригинальный пост</a>'
  links_texts = [f'<a href="{attachment.link}">{attachment.attachment_type}</a>' for attachment in attachments if attachment.attachment_type != "photo"]
  unattached_text = TextStorage.text_unattached(unattached)
  final_text = ""
  if begin: final_text+=f"{from_group_text}\n"
  final_text+= text
  if end and (len(links_texts)>0 or unattached>0): 
    final_text+=f"\n——К ПОСТУ ПРИКРЕПЛЕНЫ——"
    if len(links_texts)>0:
      final_text+=f"\n{' ; '.join(links_texts)}"
    if unattached>0:
      final_text+=f"\n{unattached_text}"
    final_text+=f"\n{TextStorage.line}"
  if end: final_text+=f"\n{post_link_text}"
  return final_text

def get_message_texts(group_name, post, attachments):
  """Returns text message to telegram channel
    :param post: VK api response"""
  CAPTION_LEN = 850
  POST_LEN = 3800
  has_photos = False
  for attachment in attachments:
    if attachment.attachment_type == "photo":
      has_photos = True
    
  if len(post.text)<=(CAPTION_LEN if has_photos else POST_LEN):
    text = parse_vk_post_text(post.text)
    text = wrap_message_text(text, post, group_name, begin = True, end=True, attachments=attachments)
    return [text]
  logger.debug(f"post text was too long, cutting it")
  text_list = []
  next_space = (post.text)[CAPTION_LEN:].find(" ")
  if next_space!=-1: split = CAPTION_LEN + next_space
  else: #go here only if we have more than 800 symbols, but also have no spaces after the splittting point
    k=50
    while split==-1:
      split = (len(post.text)-k).find(" ")#we try to find an earlier splitting point
      if k>=len(post.text):
        split = len(post.text) #if we fail at that, then just fuck it and we cut however we want
  
  text = parse_vk_post_text(post.text[:split])
  text = wrap_message_text(text, post, group_name, begin = True, end=False)
  text_list.append(text)
  N = (len(post.text)-split)//POST_LEN + 1
  for i in range(N):
    end = True if i==N-1 else False
    text = parse_vk_post_text(post.text[split+POST_LEN*i:split+POST_LEN*(i+1)])
    text = wrap_message_text(text, post, group_name, False, end, attachments)
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
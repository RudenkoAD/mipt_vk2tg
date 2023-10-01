from dataclasses import dataclass

@dataclass
class Attachment:
  link:str
  attachment_type:str

def get_video_link(attachment):
  if attachment.video is None:
    return None
  video = attachment.video
  if video.player is not None:
    return video.player
  #if video.platform is None:
  return f"https://vk.com/video{video.owner_id}_{video.id}"
  #if video.platform
  #return None

def get_photo_link(attachment):
  if attachment.photo is None:
    return None
  return max(attachment.photo.sizes, key=lambda x: x.width).url

def get_link_link(attachment):
  return attachment.link.url

def get_audio_link(attachment):
  return attachment.audio.url

def get_doc_link(attachment):
  return attachment.doc.url

def get_note_link(attachment):
  return attachment.note.view_url

def get_poll_link(attachment):
  poll = attachment.poll
  return f"https://vk.com/poll{poll.owner_id}_{poll.id}"

def handle_attachment(attachment):
  if attachment.photo is not None:
    return Attachment(get_photo_link(attachment), "photo")
  if attachment.video is not None:
    return Attachment(get_video_link(attachment), "видео")
  if attachment.link is not None:
    return Attachment(get_link_link(attachment), "ссылка")
  if attachment.audio is not None:
    return Attachment(get_audio_link(attachment), "аудио")
  if attachment.doc is not None:
    return Attachment(get_doc_link(attachment), "файл")
  if attachment.note is not None:
    return Attachment(get_note_link(attachment), "статья")
  if attachment.poll is not None:
    return Attachment(get_poll_link(attachment), "опрос")
  return None

def get_attachments_links(attachments):
  """:param attachments: VK api response - list of dicts. Each dict is attachment.
    :return: list of photos links or None if there is no photos"""
  return [i for i in [handle_attachment(attachment) for attachment in attachments] if i is not None]


if __name__ == "__main__":
  import  asyncio
  from asyncvkworker import VkFetcher
  vk_fetcher = VkFetcher()
  post = asyncio.run(vk_fetcher.get_post_by_id(-222716121, 3))
  print(get_attachments_links(post.attachments))
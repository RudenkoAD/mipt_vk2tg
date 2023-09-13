#import pip
#pip.main(["install", "python-telegram-bot[job-queue]"])
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Bot, Update  #upm package(python-telegram-bot)
from telegram.ext import CommandHandler, CallbackQueryHandler  #upm package(python-telegram-bot)
from telegram.error import RetryAfter, BadRequest, NetworkError, Forbidden  #upm package(python-telegram-bot)
from telegram.ext import ApplicationBuilder, ContextTypes  #upm package(python-telegram-bot)
from vkworker import vkfetcher
from sqliteworker import sqlcrawler
from logger import setup_logger
from secrets import TG_CREATOR_ID, TG_TOKEN
import asyncio
from time import sleep
import json
import datetime
from vk_post_parser import parse_vk_post_text
#instantiate managers
dbmanager = sqlcrawler()
vkmanager = vkfetcher(dbmanager=dbmanager)
logger = setup_logger("mipt")
# Define emojis
CHECKMARK_EMOJI = "✅"
CROSS_EMOJI = "❌"


def get_post_link(post_id: int, group_id: int):
  """Returns link to post in VK"""
  link = f"https://vk.com/wall{group_id}_{post_id}"
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


def get_message_text(group_name, post: dict, it: int = 0, max_it: int = None):
  """Returns text message to telegram channel
    :param post: VK api response    """
  CAPTION_LEN = 950
  if len(post["text"]) > CAPTION_LEN:
    if max_it is None:
      max_it = len(post["text"]) // CAPTION_LEN + 1
    it += 1
    logger.info("post text was too long, cutting it down")
    text = post["text"][:CAPTION_LEN] + f'\n({it}/{max_it})'
    post["text"] = post["text"][CAPTION_LEN:]

    return f"От {group_name}:\n\
    {text}\n\
    Оригинальный пост:{get_post_link(post['id'], post['owner_id'])}", False

  return f"От {group_name}:\n{post['text']}\nОригинальный пост:{get_post_link(post['id'], post['owner_id'])}", True

async def put_message_into_queue(chat_id, caption, media=None):
  media = json.dumps(media)
  dbmanager.put_message_into_queue(chat_id, caption, media)

async def send_message_from_queue(context):
  message = dbmanager.get_message_from_queue()
  if message is not None:
    try:
      media = [InputMediaPhoto(url) for url in  json.loads(message.media)]
    except:
      media = None
    await send_message(context.bot, chat_id=message.chat_id, caption=message.caption, media=media)
    logger.info(f"sent post from queue to user {message.chat_id}")
    dbmanager.del_message_from_queue(message.message_id)
  else:
    logger.info("no messages in queue")

async def send_message(bot: Bot, chat_id, caption, media=None):
  post_not_sent = True
  while post_not_sent:
    try:
      if (media is None) or (len(media) == 0):
        await bot.send_message(chat_id=chat_id, text=caption)
      else:
        await bot.send_media_group(chat_id=chat_id,
                                   media=media,
                                   caption=caption,
                                   read_timeout=60,
                                   write_timeout=60,
                                   parse_mode="HTML")
      post_not_sent = False
    except RetryAfter as e:
      logger.error(
        f"telegram throttled us, waiting for {e.retry_after} seconds")
      await asyncio.sleep(e.retry_after + 1)
    except Forbidden:
      logger.debug(f"user with id {chat_id} has blocked us")
      dbmanager.remove_user(chat_id)
      post_not_sent = False
    except NetworkError as e:
      logger.error(f"Network error: {e}")
      await asyncio.sleep(10)
      await send_message(bot, chat_id, caption, media)
      post_not_sent = False

async def make_post(bot: Bot, channel_id, group_name, post):
  post_text, finished = get_message_text(group_name, post)
  media = get_photos_links(post["attachments"])
  if media is None:
    await put_message_into_queue(channel_id, post_text)
    logger.debug(f"put message into queue for user {channel_id}")
  else:
    if len(media) > 10:
      media = media[:10]
    await put_message_into_queue(channel_id, post_text, media)
    logger.debug(f"put message into queue for user {channel_id}")
  if not finished: await make_post(bot, channel_id, group_name, post)

async def get_and_fetch_all(bot, dbmanager):
  logger.debug("starting the get_and_fetch_all")
  for group_id, group_name, link in dbmanager.get_groups():
    posts = vkmanager.get_new_posts(vk_id=group_id)
    for post in reversed(posts):
      logger.debug(f"posting post: {get_post_link(post['id'], group_id)}")
      for user_id in dbmanager.get_subscribers(group_id):
        await make_post(bot, user_id, group_name, post)

async def get_and_fetch_one(context):
  bot = context.bot
  group_id = context.job.data
  try:
    logger.debug(f"fetching from group_id = {group_id}")
    posts = vkmanager.get_new_posts(vk_id=group_id)
    group_name = dbmanager.get_group_name_by_id(group_id)
    for post in reversed(posts):
      logger.debug(f"starting make_post: {get_post_link(post['id'], group_id)}")
      for user_id in dbmanager.get_subscribers(group_id):
        await make_post(bot, user_id, group_name, post)
      dbmanager.update_post_id(group_id, post["id"])
    logger.debug(f"finished fetching from group_id = {group_id}")
  except Exception as e:
    logger.info(f"fetching from group_id = {group_id} failed: {e.args}")

def setup_fetchers(job_queue, bot, dbmanager):
  logger.info("started setup_fetchers")
  starttime = datetime.datetime.now()
  d = datetime.timedelta(seconds=4.5)
  num = 0
  for group_id, group_name, link in dbmanager.get_groups():
    time_to_first = num * d + starttime - datetime.datetime.now()
    num += 1
    job_queue.run_repeating(get_and_fetch_one,
                            data=group_id,
                            interval=60 * 15,
                            first=time_to_first)
  logger.info("ended setup_fetchers")


#helpers
def id(folder_name):
  return dbmanager.get_folder_id_by_name(folder_name)

def name(folder_id):
  return dbmanager.get_folder_name_by_id(folder_id)


# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  folders: list[str] = dbmanager.get_folders()
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data=f"F_{id}_0")]
              for id, folder in folders]

  await update.message.reply_text(
    '''
Привет, перед тобой бот который помогает аггрегировать все паблики, связанные с мфти в одном месте.
Просто выбери в папках ниже те группы что тебя интересуют, и нажми на них.
Бот будет пересылать тебе все посты из групп которые отмечены ✅
    ''',
    reply_markup=InlineKeyboardMarkup(keyboard))

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    text = "Объявление от адинистрации бота!\n"+' '.join(context.args)
    for user_id in dbmanager.get_all_users():
      await send_message(context.bot, user_id, text, None)
  else:
    logger.info(f"denied use of /announce to user_id = {update.effective_user.id}")
    return
  
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if context.args == []:
    await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text="Пожалуйста используйте эту команду с аргументом:\n/contact <ваш текст>")
  else:
    await context.bot.send_message(chat_id=TG_CREATOR_ID,
                                   text="@" + update.effective_user.username +
                                   ": " + " ".join(context.args))
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Передали все что вы написали")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await answer_query_if_not_expired(query)
  folders: list[str] = dbmanager.get_folders(parent=None)
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data=f"F_{id}_0")]
              for id, folder in folders]
  try:
    await query.edit_message_text(text=query.message.text,
                                  reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    logger.error(e)

async def answer_query_if_not_expired(query):
  try:
    await query.answer()
    return 1
  except:
    return 0


#commands to handle bot navigation
async def folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_user.id
  logger.debug(f"FOLDER for user_id = {user_id}")
  await answer_query_if_not_expired(query)
  folder_id = int(query.data.split("_")[1])
  folder_page = int(query.data.split("_")[2])
  folder = name(folder_id)
  data = dbmanager.get_groups_from_folder(folder)
  subfolders = dbmanager.get_folders(parent=folder)
  parent = dbmanager.get_parent(folder)
  pagedownbutton = InlineKeyboardButton(
    "<", callback_data=f"F_{folder_id}_{max(folder_page-1, 0)}")
  pageupbutton = InlineKeyboardButton(
    ">", callback_data=f"F_{folder_id}_{folder_page+1}")
  backbutton = InlineKeyboardButton(
    "Назад", callback_data="MENU") if parent is None else InlineKeyboardButton(
      "Назад", callback_data=f"F_{id(parent)}_0")

  keyboard = \
  [[InlineKeyboardButton(f"{subfolder}", callback_data=f"F_{id(subfolder)}_0")]
    for ids, subfolder in subfolders if folder_page==0]+\
  [[InlineKeyboardButton(f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(user_id, group) else CROSS_EMOJI} {group}",
                         callback_data=f"G_{id(folder)}_{ids}_{folder_page}"), InlineKeyboardButton("ССЫЛКА", url=link)] for ids, group, link in data[folder_page*5:folder_page*5+5]]
  if len(data) > 5:
    if folder_page == 0:
      keyboard += [[pageupbutton]]
    elif folder_page * 5 + 5 > len(data):
      keyboard += [[pagedownbutton]]
    else:
      keyboard += [[pagedownbutton, pageupbutton]]
  keyboard += [[backbutton]]
  try:
    await query.edit_message_text(text=query.message.text,
                                  reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    logger.error(e)

async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_user.id
  logger.debug(f"GROUP for user_id = {user_id}")
  await answer_query_if_not_expired(query)
  dbmanager.flip_subscribe(user_id, int(query.data.split("_")[2]))
  folder_id = int(query.data.split("_")[1])
  folder_page = int(query.data.split("_")[3])
  folder = name(folder_id)

  data = dbmanager.get_groups_from_folder(folder=folder)
  subfolders = dbmanager.get_folders(parent=folder)
  parent = dbmanager.get_parent(folder)

  pagedownbutton = InlineKeyboardButton(
    "<", callback_data=f"F_{folder_id}_{max(folder_page-1, 0)}")
  pageupbutton = InlineKeyboardButton(
    ">", callback_data=f"F_{folder_id}_{folder_page+1}")
  backbutton = InlineKeyboardButton(
    "Назад", callback_data="MENU") if parent is None else InlineKeyboardButton(
      "Назад", callback_data=f"F_{id(parent)}_0")

  keyboard = [[
    InlineKeyboardButton(f"{subfolder}", callback_data=f"F_{id(subfolder)}_0")
  ] for ids, subfolder in subfolders if folder_page == 0]
  keyboard += [[
    InlineKeyboardButton(
      f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(user_id, group) else CROSS_EMOJI} {group}",
      callback_data=f"G_{id(folder)}_{ids}_{folder_page}"),
    InlineKeyboardButton("ССЫЛКА", url=link)
  ] for ids, group, link in data[folder_page * 5:folder_page * 5 + 5]]
  if len(data) > 5:
    if folder_page == 0:
      keyboard += [[pageupbutton]]
    elif folder_page * 5 + 5 > len(data):
      keyboard += [[pagedownbutton]]
    else:
      keyboard += [[pagedownbutton, pageupbutton]]
  keyboard += [[backbutton]]
  try:
    await query.edit_message_text(text=query.message.text,
                                  reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    logger.error(e)

def main():
  print("starting")
  application = ApplicationBuilder().token(TG_TOKEN).build()
  job_queue = application.job_queue
  logger.info("adding handlers")
  application.add_handler(CommandHandler('start', start))
  application.add_handler(CommandHandler('contact', contact))
  application.add_handler(CommandHandler('announce', announce))
  application.add_handler(CallbackQueryHandler(menu, pattern="^MENU$"))
  application.add_handler(CallbackQueryHandler(folder, pattern="^F"))
  application.add_handler(CallbackQueryHandler(group, pattern="^G"))

  setup_fetchers(job_queue, application.bot, dbmanager)
  job_queue.run_repeating(send_message_from_queue,
                            interval=30)
  logger.info("starting app")
  application.run_polling(allowed_updates=Update.ALL_TYPES)
  logger.info("ended app")


if __name__ == '__main__':
  main()

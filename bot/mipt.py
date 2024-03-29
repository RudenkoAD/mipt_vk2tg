#import pip
#pip.main(["install", "python-telegram-bot[job-queue]"])
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Bot, Update  #upm package(python-telegram-bot)
from telegram.ext import CommandHandler, CallbackQueryHandler  #upm package(python-telegram-bot)
from telegram.error import RetryAfter, BadRequest, NetworkError, Forbidden   #upm package(python-telegram-bot)
from telegram.ext import ApplicationBuilder, ContextTypes  #upm package(python-telegram-bot)
from logger import setup_logger, clear_logs
clear_logs()
from asyncvkworker import VkFetcher
from sqliteworker import sqlcrawler
from secrets import TG_CREATOR_ID, TG_TOKEN
import asyncio
from time import sleep
import json
import datetime
from attachmentmanager import get_attachments_links
from vk_post_parser import get_post_link, get_message_texts
from text_storage import TextStorage
from aiohttp.client_exceptions import ClientOSError, ClientConnectionError
from classes import Group, Folder, Link, QueueMessage
from vkbottle.exception_factory import VKAPIError
from random import randint
import urllib.request
import os
#instantiate managers
dbmanager = sqlcrawler()
vkmanager = VkFetcher(dbmanager=dbmanager)
logger = setup_logger("mipt")
# Define emojis
UNSUBSCRIBED = "❌"
SUBSCRIBED_WITH_NOTIFICATIONS = "🔊"
SUBSCRIBED_WITHOUT_NOTIFICATIONS = "🔇"
import sys
import traceback

async def handle_exception(bot):
    error_type, error_value, error_traceback = sys.exc_info()
    last_frame = traceback.extract_tb(error_traceback)[-1]
    file_name = last_frame.filename
    error_line = last_frame.lineno
    root_error_tb = traceback.extract_tb(error_traceback)[0]
    root_file_name = root_error_tb.filename
    root_line = root_error_tb.lineno
    root_error = traceback.format_exception(error_type, error_value, error_traceback)[-1].strip()
    message = f"{error_value}\n{file_name}: Line {error_line}\nRoot Error ({root_file_name}: Line {root_line}): {root_error}"
    logger.error(message)
    await send_message(bot, TG_CREATOR_ID, message, None)

  
async def put_message_into_queue(user_ids, caption, media=None, notifications=None):
  if notifications is None:
    notifications = [True for i in user_ids]
  media = json.dumps(media)
  for i in range(len(user_ids)):
    dbmanager.put_message_into_queue(user_ids[i], caption, media, notifications[i])

async def send_message_from_queue(context):
  logger.debug("starting send_message_from_queue")
  message = dbmanager.get_message_from_queue()
  if message is not None:
    try:
      medias = json.loads(message.media)
      if medias is None: medias = []
      #if the url failed previously and we've cached the media, upload it
      media = []
      for url in medias:
        if f"{url}.jpg" in os.listdir("data"):
          media.append(InputMediaPhoto(open({url}.jpg, "rb")))
        else:#if the media is not cached, try to get it from url
          media.append(InputMediaPhoto(url))
          
    except Exception:
      await handle_exception(context.bot)
      media = []
    await send_message(context.bot, chat_id=message.chat_id, caption=message.caption, media=media, silent=not bool(message.notifications))
    logger.info(f"sent post from queue to user {message.chat_id}")
    dbmanager.del_message_from_queue(message.message_id)
  else:
    logger.info("no messages in queue")

async def send_message(bot: Bot, chat_id, caption, media=None, silent=False):
    """Sends a message to a specified chat_id with optional media"""
    logger.debug("starting send_message")
    if caption == "" or caption is None:
        return
    while True:
        try:
            if media:
                await bot.send_media_group(
                    chat_id=chat_id,
                    media=media,
                    caption=caption,
                    parse_mode="HTML",
                    api_kwargs={"disable_web_page_preview": True},
                    disable_notification=silent,
                    read_timeout=10,
                    write_timeout=10,
                    connect_timeout=10,
                    pool_timeout=10
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    disable_notification=silent,
                    disable_web_page_preview=True,
                    read_timeout=10,
                    write_timeout=10,
                    connect_timeout=10,
                    pool_timeout=10
                )
            break
            
        except RetryAfter as e:
            logger.error(f"telegram throttled us, waiting for {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after + 1)            
        except Forbidden:
            logger.warning(f"user with id {chat_id} has blocked us")
            dbmanager.remove_user(chat_id)
            break
        except BadRequest as e:
          handle_exception(bot)
          if ("user_is_blocked" in str(e)):
            dbmanager.remove_user(chat_id)
            break
        except NetworkError as e:
            logger.error(f"Network error: {e}")
            if ("Chat not found" in str(e)):
              dbmanager.remove_user(chat_id)
              break
            if (("wrong file identifier/http url specified" in str(e)) or ("wrong type of the web page content" in str(e))):
              all_files = os.listdir("data")
              for f in all_files:
                os.remove(os.path.join("data", f))
              #download new photos
              for photo in media:
                urllib.request.urlretrieve(photo.media, f"{photo.media}.jpg")
            await handle_exception(bot)
        except TimeoutError as e:
            await handle_exception(bot)
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Unknown error: {e}")
            await handle_exception(bot)
            await asyncio.sleep(30)

async def wrap_and_put_into_queue(user_ids, group_name, post, notifications_list):
    """Wraps a post and puts it into the queue for each user id in the list"""
    media = get_attachments_links(post.attachments)
    # limit media to 10 links only
    media = media[:10]
    if len(media) > 10:
        logger.warning("we've just cut the media, check this post")
    photos = [i.link for i in media if i.attachment_type == "photo"]
    post_texts = get_message_texts(group_name, post, media)
    for i, post_text in enumerate(post_texts):
        await put_message_into_queue(user_ids, post_text, photos if i == 0 else None, notifications=notifications_list)
        logger.debug(f"put message into queue for users {user_ids}")



async def get_and_fetch_one(context):
  bot = context.bot
  group_id = context.job.data
  try:
    logger.debug(f"fetching from group_id = {group_id}")
    posts = await vkmanager.get_new_posts(vk_id=group_id)
    for post in reversed(posts):
      await handle_post(post)
    logger.debug(f"finished fetching from group_id = {group_id}")
  except ClientOSError as e:
      pass
  except ClientConnectionError as e:
      pass
  except VKAPIError as e:
    await asyncio.sleep(10)
  except Exception as e:
    logger.error(f"fetching from group_id = {group_id} failed: {e.args}")
    await handle_exception(context.bot)

async def handle_post(post):
    """Wraps a post and puts it into the queue for each user id in the list"""
    group_id = post.owner_id
    logger.debug(f"starting make_post: {get_post_link(post.id, group_id)}")
    
    group_name = dbmanager.get_group_by_id(group_id).group_name
    user_ids = dbmanager.get_subscribers(group_id)
    notifications_list = [dbmanager.subscription_status(user_id, post.owner_id) == 1 for user_id in user_ids]
    await wrap_and_put_into_queue(user_ids, group_name, post, notifications_list)
    
    if post.copy_history is not None:
        for repost in post.copy_history:
            await handle_repost(repost, user_ids=user_ids, group_name="репоста, прикеплённого к посту выше", notifications_list=notifications_list) #recursion if there is a repost inside this post
    
    dbmanager.update_post_id(group_id, post.id)

async def handle_repost(post, user_ids, group_name, notifications_list):
    """Wraps a post and puts it into the queue for each user id in the list"""
    group_id = post.owner_id
    logger.debug(f"starting make_post: {get_post_link(post.id, group_id)}")
    await wrap_and_put_into_queue(user_ids, group_name, post, notifications_list)

def setup_fetchers(job_queue, dbmanager:sqlcrawler):
  logger.info("started setup_fetchers")
  starttime = datetime.datetime.now()
  d = datetime.timedelta(seconds=3)
  num = 1
  for group in dbmanager.get_groups():
    time_to_first = num * d + starttime - datetime.datetime.now()
    num += 1
    job_queue.run_repeating(get_and_fetch_one,
                            data=group.group_id,
                            interval=60 * 15,
                            first=time_to_first)
  logger.info("ended setup_fetchers")


# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  folders = dbmanager.get_folders()
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder.folder_name, callback_data=f"F_{folder.folder_id}_0")]
              for folder in folders]

  await update.message.reply_text(
    TextStorage.start_menu_text,
    reply_markup=InlineKeyboardMarkup(keyboard))

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    num = update.message.text.find('\n')
    text = update.message.text[num+1:]
    for user_id in dbmanager.get_all_user_ids():
      await send_message(context.bot, user_id, text, None, silent=False)
  else:
    logger.info(f"denied use of /announce to user_id = {update.effective_user.id}")
    return
  
async def announce_silent(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    num = update.message.text.find('\n')
    text = update.message.text[num+1:]
    for user_id in dbmanager.get_all_user_ids():
      await send_message(context.bot, user_id, text, None, silent=True)
  else:
    logger.info(f"denied use of /announce_silent to user_id = {update.effective_user.id}")
    return

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    users = dbmanager.get_all_user_ids()
    text = str(len(users))#+'\n'+"\n".join([f"[{user_id}](tg://user?id={user_id})" for user_id in users])
    await context.bot.send_message(TG_CREATOR_ID, text)
  else:
    logger.info(f"denied use of /list to user_id = {update.effective_user.id}")
    return

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
  '''
  a command that finds a group by name and shows the user the same type of layout as in /start to subscibe to it
  '''
  if context.args == []:
    await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text="Пожалуйста используйте эту команду с аргументом:\n/find <название группы>")
  else:
    group_name = " ".join(context.args)
    groups = dbmanager.search_groups(group_name)
    user_id = update.effective_chat.id
    if groups == []:
      await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Ничего не найдено, попробуйте другое название")
    else:
      keyboard = [[InlineKeyboardButton(f"{get_emoji(user_id, group.group_id)} {group.group_name}",
                         callback_data=f"S_{group.group_id}"), InlineKeyboardButton("ССЫЛКА", url=group.group_link)] for group in groups]
      await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Вот что я нашёл:\nЕсли ваша группа не в списке, то попробуйте более точное название, или напишите в /contact и я добавлю её",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def react_to_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await answer_query_if_not_expired(query)
  group_id = int(query.data.split("_")[1])
  user_id = query.from_user.id
  group_name = dbmanager.get_group_by_id(group_id).group_name
  groups = dbmanager.search_groups(group_name)
  dbmanager.change_subscribe(user_id, group_id)
  keyboard = [[InlineKeyboardButton(f"{get_emoji(user_id, group.group_id)} {group.group_name}",
                         callback_data=f"S_{group.group_id}"), InlineKeyboardButton("ССЫЛКА", url=group.group_link)] for group in groups]
  await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

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
  folders = dbmanager.get_folders(None)
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder.folder_name, callback_data=f"F_{folder.folder_id}_0")]
              for folder in folders]
  try:
    await query.edit_message_text(text=TextStorage.start_menu_text,
                                  reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    await handle_exception(context.bot)
    logger.error(e)

async def answer_query_if_not_expired(query):
  try:
    await query.answer()
    return 1
  except Exception:
    return 0

def get_emoji(user_id, group_id):
  if dbmanager.subscription_status(user_id, group_id) == 1:
    return SUBSCRIBED_WITH_NOTIFICATIONS
  elif dbmanager.subscription_status(user_id, group_id) == 2:
    return SUBSCRIBED_WITHOUT_NOTIFICATIONS
  else:
    return UNSUBSCRIBED

async def draw_folder(query, user_id ,folder_id, folder_page):
  folder = dbmanager.get_folder_by_id(folder_id)
  data = dbmanager.get_groups_from_folder_name(folder.folder_name)
  subfolders = dbmanager.get_folders(folder.folder_name)
  parent_name = folder.parent_name
  text = folder.folder_text if folder.folder_text else query.message.text
  pagedownbutton = InlineKeyboardButton(
    "<", callback_data=f"F_{folder_id}_{max(folder_page-1, 0)}")
  pageupbutton = InlineKeyboardButton(
    ">", callback_data=f"F_{folder_id}_{folder_page+1}")
  backbutton = InlineKeyboardButton(
    "Назад", callback_data="MENU") if parent_name is None else InlineKeyboardButton(
      "Назад", callback_data=f"F_{dbmanager.get_folder_by_name(parent_name).folder_id}_0")

  keyboard = \
  [[InlineKeyboardButton(f"{subfolder.folder_name}", callback_data=f"F_{subfolder.folder_id}_0")]
    for subfolder in subfolders if folder_page==0]+\
  [[InlineKeyboardButton(f"{get_emoji(user_id, group.group_id)} {group.group_name}",
                         callback_data=f"G_{folder.folder_id}_{group.group_id}_{folder_page}"), InlineKeyboardButton("ССЫЛКА", url=group.group_link)] for group in data[folder_page*5:folder_page*5+5]]
  if len(data) > 5:
    if folder_page == 0:
      keyboard += [[pageupbutton]]
    elif folder_page * 5 + 5 >= len(data):
      keyboard += [[pagedownbutton]]
    else:
      keyboard += [[pagedownbutton, pageupbutton]]
  keyboard += [[backbutton]]
  try:
    await query.edit_message_text(text=text,
                                  reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    await handle_exception(query.bot)
    logger.error(e)

#commands to handle bot navigation
async def folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_chat.id
  logger.debug(f"FOLDER for user_id = {user_id}")
  await answer_query_if_not_expired(query)
  folder_id = int(query.data.split("_")[1])
  folder_page = int(query.data.split("_")[2])
  await draw_folder(query, user_id, folder_id, folder_page)

async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_chat.id
  logger.debug(f"GROUP for user_id = {user_id}")
  await answer_query_if_not_expired(query)
  folder_id = int(query.data.split("_")[1])
  folder_page = int(query.data.split("_")[3])
  dbmanager.change_subscribe(user_id, int(query.data.split("_")[2]))
  await draw_folder(query, user_id, folder_id, folder_page)

#admin commands

async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text="""команды админа:
/list
/announce
/announce_silent
/add_folder
/add_group
""")
    exit(0)
  else:
    logger.info(f"denied use of /stop to user_id = {update.effective_user.id}")
    return

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text="Бот остановлен")
    exit(0)
  else:
    logger.info(f"denied use of /stop to user_id = {update.effective_user.id}")
    return

async def add_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    if context.args==[]:
      await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Пожалуйста используйте эту команду с аргументом:\n/add_folder\n<название папки>\n<название parent-папки>")
      return
    try:
      texts = update.message.text.split("\n")
      name = texts[1]
      parent = texts[2] if len(texts)>2 else None
      dbmanager.insert_folder(name, parent if parent else None)
      dbmanager.insert_folder(context.args[0], context.args[1] if len(context.args)>1 else None)
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text="Папка добавлена")
    except:
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text="Что-то пошло не так. Не забывай что аргументы через enter")
  
  return

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id==TG_CREATOR_ID:
    if len(context.args)<4:
      await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Пожалуйста используйте эту команду с аргументом:\n/add_group\n<название группы>\n<id группы>\n<ссылка на группу>\n<название папки>")
    else:
      texts = update.message.text.split("\n")
      dbmanager.insert_group(texts[1], texts[2], texts[3], texts[4])
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text="Группа добавлена")
  return

def main():
  print("starting")

  application = ApplicationBuilder().token(TG_TOKEN).build()
  job_queue = application.job_queue
  logger.info("adding handlers")
  application.add_handler(CommandHandler('start', start))
  application.add_handler(CommandHandler('stop', stop))
  application.add_handler(CommandHandler('contact', contact))
  application.add_handler(CommandHandler('announce', announce))
  application.add_handler(CommandHandler('announce_silent', announce))
  application.add_handler(CommandHandler('help', adminhelp))
  application.add_handler(CommandHandler('list', list_users))
  application.add_handler(CommandHandler('find', find))
  application.add_handler(CommandHandler('add_folder', add_folder))
  application.add_handler(CommandHandler('add_group', add_group))
  application.add_handler(CallbackQueryHandler(menu, pattern="^MENU$"))
  application.add_handler(CallbackQueryHandler(folder, pattern="^F"))
  application.add_handler(CallbackQueryHandler(react_to_find, pattern="^S"))
  application.add_handler(CallbackQueryHandler(group, pattern="^G"))

  setup_fetchers(job_queue, dbmanager)
  job_queue.run_repeating(send_message_from_queue,
                            interval=0.3)
  logger.info("starting app")
  application.run_polling(allowed_updates=Update.ALL_TYPES)
  logger.info("ended app")


if __name__ == '__main__':
  main()

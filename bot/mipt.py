#import pip
#pip.main(["install", "python-telegram-bot[job-queue]"])
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Bot, Update  #upm package(python-telegram-bot)
from telegram.ext import CommandHandler, CallbackQueryHandler  #upm package(python-telegram-bot)
from telegram.error import RetryAfter, BadRequest, NetworkError, Forbidden  #upm package(python-telegram-bot)
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
#instantiate managers
dbmanager = sqlcrawler()
vkmanager = VkFetcher(dbmanager=dbmanager)
logger = setup_logger("mipt")
# Define emojis
CHECKMARK_EMOJI = "✅"
CROSS_EMOJI = "❌"
import traceback

async def handle_exception(bot):
  text = traceback.format_exc()
  await send_message(bot, TG_CREATOR_ID, text, None)

  
async def put_message_into_queue(user_ids, caption, media=None):
  media = json.dumps(media)
  for user_id in user_ids:
    dbmanager.put_message_into_queue(user_id, caption, media)

async def send_message_from_queue(context):
  message = dbmanager.get_message_from_queue()
  if message is not None:
    try:
      medias = json.loads(message.media)
      if medias is None: medias = []
      media = [InputMediaPhoto(url) for url in medias]
    except Exception:
      await handle_exception(context.bot)
      media = []
    await send_message(context.bot, chat_id=message.chat_id, caption=message.caption, media=media)
    logger.info(f"sent post from queue to user {message.chat_id}")
    dbmanager.del_message_from_queue(message.message_id)
  else:
    logger.info("no messages in queue")

async def send_message(bot: Bot, chat_id, caption, media=None, silent=False):
  post_not_sent = True
  while post_not_sent:
    try:
      if (media is None) or (len(media) == 0):
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", disable_notification=silent, disable_web_page_preview=True)
      else:
        await bot.send_media_group(chat_id=chat_id,
                                   media=media,
                                   caption=caption,
                                   read_timeout=60,
                                   write_timeout=60,
                                   parse_mode="HTML",
                                   api_kwargs={"disable_web_page_preview":True},
                                   disable_notification=silent)
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
      await handle_exception(bot)
      await asyncio.sleep(1800)
      await send_message(bot, chat_id, caption, media)
      post_not_sent = False
    except Exception as e:
      await handle_exception(bot)
      await asyncio.sleep(1800)
      await send_message(bot, chat_id, caption, media)
      post_not_sent = False

async def wrap_and_put_into_queue(user_ids, group_name, post):
  media = get_attachments_links(post.attachments)
  if len(media) > 10:
    logger.warning("we've just cut the media, check this post")
    media = media[:10]
  photos = [i.link for i in media if i.attachment_type=="photo"]
  post_texts = get_message_texts(group_name, post, media)
  for i, post_text in enumerate(post_texts):
    if i>0:
      await put_message_into_queue(user_ids, post_text)
      logger.debug(f"put message into queue for users {user_ids}")
    else:
      await put_message_into_queue(user_ids, post_text, photos)
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
  except Exception as e:
    logger.error(f"fetching from group_id = {group_id} failed: {e.args}")
    await handle_exception(context.bot)

async def handle_post(post, special_user_destination = None, special_group_name = None):
  group_id = post.owner_id
  logger.debug(f"starting make_post: {get_post_link(post.id, group_id)}")
  group_name = dbmanager.get_group_by_id(group_id).group_name if special_group_name is None else special_group_name
  user_ids = dbmanager.get_subscribers(group_id) if special_user_destination is None else special_user_destination
  
  await wrap_and_put_into_queue(user_ids, group_name, post)
  
  if post.copy_history is not None:
    for repost in post.copy_history:
      await handle_post(repost, special_user_destination=user_ids, special_group_name = "репоста, прикрепленного к посту выше")#recursion if there is a repost inside this post
    
  dbmanager.update_post_id(group_id, post.id)
  

def setup_fetchers(job_queue, dbmanager:sqlcrawler):
  logger.info("started setup_fetchers")
  starttime = datetime.datetime.now()
  d = datetime.timedelta(seconds=1)
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
  [[InlineKeyboardButton(f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(user_id, group.group_id) else CROSS_EMOJI} {group.group_name}",
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
  dbmanager.flip_subscribe(user_id, int(query.data.split("_")[2]))
  await draw_folder(query, user_id, folder_id, folder_page)

def main():
  print("starting")
  application = ApplicationBuilder().token(TG_TOKEN).build()
  job_queue = application.job_queue
  logger.info("adding handlers")
  application.add_handler(CommandHandler('start', start))
  application.add_handler(CommandHandler('contact', contact))
  application.add_handler(CommandHandler('announce', announce))
  application.add_handler(CommandHandler('announce_silent', announce))
  application.add_handler(CommandHandler('list', list_users))
  application.add_handler(CallbackQueryHandler(menu, pattern="^MENU$"))
  application.add_handler(CallbackQueryHandler(folder, pattern="^F"))
  application.add_handler(CallbackQueryHandler(group, pattern="^G"))

  setup_fetchers(job_queue, dbmanager)
  job_queue.run_repeating(send_message_from_queue,
                            interval=1)
  logger.info("starting app")
  application.run_polling(allowed_updates=Update.ALL_TYPES)
  logger.info("ended app")


if __name__ == '__main__':
  main()

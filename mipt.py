from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram.error import RetryAfter
from config import tg_config
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from vkworker import vkfetcher
from sqlworker import sqlcrawler
from asyncio import sleep
from classes import User, Link
import json
from logger import setup_logger
#instantiate managers
dbmanager = sqlcrawler()
vkmanager = vkfetcher(dbmanager=dbmanager)
logger = setup_logger("mipt.log")
# Define emojis
CHECKMARK_EMOJI = "✅"
CROSS_EMOJI = "❌"

def get_post_link(post_id: int, group_id: int):
    """Returns link to post in VK"""
    link = f"https://vk.com/wall{group_id}_{post_id}"
    return link

def get_photos_links(attachments: list[dict]) -> list[str] | None:
    """:param attachments: VK api response - list of dicts. Each dict is attachment.
    :return: list of photos links or None if there is no photos"""
    if attachments is None or len(attachments) == 0:
        logger.debug("found no photos in attachments")
        return None
    return [attachment["photo"]["sizes"][-1]["url"] for attachment in attachments if attachment["type"] == "photo"]

def get_message_text(group_name, post: dict):
    """Returns text message to telegram channel
    :param post: VK api response    """
    if len(post["text"]) > 3000:
        logger.info("post text was too long, cutting it down")
        post["text"] = post["text"][:3000] + "..."
    return f"От {group_name}:\n{post['text']}\n{get_post_link(post['id'], post['owner_id'])}"

async def make_post(bot: Bot, channel_id, group_name, post):
    post_text = get_message_text(group_name, post)
    image_urls = get_photos_links(post["attachments"])
    if image_urls is None:
        logger.debug("found no photos in attachments")
        await bot.send_message(chat_id=channel_id, text=post_text)
        return 0
    media = [InputMediaPhoto(url) for url in image_urls]
    if len(media) > 10:
        media = media[:10]
    if len(media) == 0:
        await bot.send_message(chat_id=channel_id, text=post_text)
    post_not_sent = True
    while post_not_sent:
        try:
            await bot.send_media_group(chat_id=channel_id,
                                       media=media,
                                       caption=post_text,
                                       read_timeout=60,
                                       write_timeout=60,
                                       parse_mode="HTML")
            post_not_sent = False
        except RetryAfter as e:
            print("error")
            await sleep(e.retry_after + 1)


async def get_and_fetch_all(context):
    logger.штащ(f"starting the get_and_fetch_all")
    for group_id, group_name, link in dbmanager.get_groups():
      posts = vkmanager.get_new_posts(vk_id = group_id)
      for post in reversed(posts):
        logger.debug(f"posting post: {get_post_link(post)}")
        for user_id in dbmanager.get_subscribers(group_id):
          await make_post(context.bot, user_id, group_name, post)
          await sleep(0.5)

#helpers
def id(folder_name):
  return dbmanager.get_folder_id_by_name(folder_name)

def name(folder_id):
  return dbmanager.get_folder_name_by_id(folder_id)
# Commands for the main menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  folders:list[str] = dbmanager.get_folders()
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data=f"F_{id}")] for id, folder in folders]

  await update.message.reply_text(
    'Привет, перед тобой бот который помогает аггрегировать все паблики, связанные с мфти в одном месте. Сейчас бот на очень ранней стадии, поэтому в нем могут встречаться баги. Кроме того, сейчас в боте далеко не все важные паблики. Про многие я могу даже не знать. Поэтому про любые ошибки, пропущенные паблики, или просто свои пожелания для бота вы можете написать мне командой /contact', 
    reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  folders:list[str] = dbmanager.get_folders(parent = None)
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data=f"F_{id}")] for id, folder in folders]
  try:
    await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
    logger.error(e)
#commands to handle bot navigation
async def folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_user.id
  await query.answer()
  folder_id = int(query.data.split("_")[1])
  folder = name(folder_id)
  data = dbmanager.get_groups_from_folder(folder)
  subfolders = dbmanager.get_folders(parent = folder)
  parent = dbmanager.get_parent(folder)
  
  backbutton = InlineKeyboardButton("Меню", callback_data = "MENU") if parent is None else InlineKeyboardButton("Назад", callback_data = f"F_{id(parent)}")
  
  keyboard = \
  [[InlineKeyboardButton(f"{subfolder}", callback_data=f"F_{id(subfolder)}")]
    for ids, subfolder in subfolders]+\
  [[InlineKeyboardButton(f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(user_id, group) else CROSS_EMOJI} {group}", 
                         callback_data=f"G_{id(folder)}_{ids}")] for ids, group, link in data]+\
  [[backbutton]]
  #, InlineKeyboardButton(f"ССЫЛКА", url=link)
  try:
    await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
     logger.error(e)

async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = update.effective_user.id
  await query.answer()
  dbmanager.flip_subscribe(user_id, int(query.data.split("_")[2]))
  folder_id = int(query.data.split("_")[1])
  folder = name(folder_id)

  data = dbmanager.get_groups_from_folder(folder = folder)
  subfolders = dbmanager.get_folders(parent = folder)
  parent = dbmanager.get_parent(folder)

  backbutton = InlineKeyboardButton("Меню", callback_data = "MENU") if parent is None else InlineKeyboardButton("Назад", callback_data = f"F_{id(parent)}")
  
  keyboard = \
  [[InlineKeyboardButton(f"{subfolder}", callback_data=f"F_{id}")]
    for id, subfolder in subfolders]+\
  [[InlineKeyboardButton(f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(user_id, group) else CROSS_EMOJI} {group}", 
                         callback_data=f"G_{folder_id}_{ids}")] for ids, group, link in data]+\
  [[backbutton]]
  #, InlineKeyboardButton(f"ССЫЛКА", url=link)
  try:
     await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
  except Exception as e:
     logger.error(e)


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if context.args == []:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста используйте эту команду с аргументом:\n/contact <ваш текст>")
  else:
    await context.bot.send_message(chat_id=tg_config.creator_id, text="@"+update.effective_user.username+": "+" ".join(context.args))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Передали все что вы написали") 
# Set up the Telegram bot
def main():
  application = ApplicationBuilder().token(tg_config.token).build()
  job_queue = application.job_queue
  #mipt schools setup
  application.add_handler(CommandHandler('start', start))
  application.add_handler(CommandHandler('contact', contact))
  application.add_handler(CallbackQueryHandler(menu, pattern="^MENU$"))
  application.add_handler(CallbackQueryHandler(folder, pattern="^F"))
  application.add_handler(CallbackQueryHandler(group, pattern="^G"))
  #set up fetching
  job_queue.run_repeating(get_and_fetch_all, interval=60*15, first=10)
  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
  main()

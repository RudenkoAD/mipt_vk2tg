from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from config import tg_config
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from vkworker import vkfetcher
from sqlworker import sqlcrawler
from asyncio import sleep
from classes import User, Link
import json
#instantiate managers
dbmanager = sqlcrawler()
vkmanager = vkfetcher(dbmanager=dbmanager)

# Define emojis
CHECKMARK_EMOJI = "✅"
CROSS_EMOJI = "❌"

async def get_and_fetch_all(context):
    print(dbmanager.get_groups())
    for group_id, group_name in dbmanager.get_groups():
      posts = vkmanager.get_new_posts(vk_id = group_id)
      for user_id in dbmanager.get_subscribers(group_id):
        for post in reversed(posts):
          await context.bot.sendMessage(chat_id=user_id, text=f"От {group_name}:\n"+post['text'])
          await sleep(1)

# Commands for the main menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  folders:list[str] = dbmanager.get_folders()
  print(folders)
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data="FOLDER_"+folder)] for folder in folders]
  print(keyboard)
  await update.message.reply_text(
    'Привет, я бот который помогает аггрегировать все интересные тебе паблики, связанные с мфти в одном месте. Сейчас бот на очень ранней стадии, поэтому в нем могут встречаться баги. про любые ошибки (или просто так), вы можете написать создателю командой /contact', 
    reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  folders:list[str] = dbmanager.get_folders()
  # Create the keyboard layout
  keyboard = [[InlineKeyboardButton(folder, callback_data="FOLDER_"+folder)] for folder in folders]
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
#commands to handle bot navigation
async def folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  id = update.effective_user.id
  await query.answer()
  folder = query.data.split("_")[1]
  groups = dbmanager.get_groups_from_folder(folder = folder)
  subfolders = dbmanager.get_subfolders(folder = folder)
  keyboard = \
  #[[InlineKeyboardButton(f"{subfolder}", callback_data=f"SUBFOLDER_{folder}_{subfolder}_{group}")]
  #  for subfolder in subfolders]+\
  [[InlineKeyboardButton(f"{group}", callback_data=f"GROUP_{folder}_{group}")]
    for group in groups]+\
  [[InlineKeyboardButton("Меню", callback_data = "MENU")]]
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  id = update.effective_user.id
  await query.answer()
  folder = query.data.split("_")[1]
  group = query.data.split("_")[2]
  dbmanager.flip_subscribe(id, group)
  groups = dbmanager.get_groups_from_folder(folder = folder)
  keyboard = [
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if dbmanager.is_subscribed(id, group) else CROSS_EMOJI} {group}", callback_data=f"GROUP_{folder}_{group}")]
    for group in groups]+[[InlineKeyboardButton("Меню", callback_data = "MENU")]]
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if context.args == []:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста используйте эту команду с аргументом:\n/contact <ваш текст>")
  else:
    await context.bot.send_message(chat_id=tg_config.creator_id, text="@"+update.effective_user.username+": "+" ".join(context.args))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Передали создателю все что вы написали") 
#async def subfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
# Set up the Telegram bot
def main():
  application = ApplicationBuilder().token(tg_config.token).build()
  job_queue = application.job_queue
  #mipt schools setup
  application.add_handler(CommandHandler('start', start))
  application.add_handler(CommandHandler('contact', contact))
  application.add_handler(CallbackQueryHandler(menu, pattern="^MENU$"))
  application.add_handler(CallbackQueryHandler(folder, pattern="^FOLDER"))
  application.add_handler(CallbackQueryHandler(group, pattern="^GROUP"))
  #set up fetching
  job_queue.run_repeating(get_and_fetch_all, interval=60*15, first=1)
  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
  main()

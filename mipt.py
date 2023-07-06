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
    for group_id, group_name, link in dbmanager.get_groups():
      posts = vkmanager.get_new_posts(vk_id = group_id)
      for user_id in dbmanager.get_subscribers(group_id):
        for post in reversed(posts):
          await context.bot.sendMessage(chat_id=user_id, text=f"От {group_name}:\n"+post['text'])
          await sleep(1)

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
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
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
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))

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
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))


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
  job_queue.run_repeating(get_and_fetch_all, interval=60*15, first=120)
  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
  main()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from config import tg_config
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from vkworker import vkfetcher
from asyncio import sleep
from classes import User, Link
import json
#instantiate vk manager
vkmanager = vkfetcher()

#load json of vk groups
with open("groups.json") as f:
  groups = json.load(f)

# Define emojis
CHECKMARK_EMOJI = "✅"
CROSS_EMOJI = "❌"

# Define the UI commands
async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Create the keyboard layout
  keyboard = [
    [InlineKeyboardButton("ЛФИ", callback_data="ЛФИ")],
    [InlineKeyboardButton("ФПМИ", callback_data="ФПМИ")],
    [InlineKeyboardButton("ФРКТ", callback_data="ФРКТ")],
    [InlineKeyboardButton("ФБМФ", callback_data="ФБМФ")]
  ]

  reply_markup = InlineKeyboardMarkup(keyboard)

  # Send the options menu to the user
  await update.message.reply_text('Привет, я бот который помогает аггрегировать все интересные тебе паблики, связанные с мфти в одном месте. Сейчас бот на очень ранней стадии, поэтому в нем могут встречаться баги. про любые ошибки (или просто так), вы можете написать создателю командой /contact', reply_markup=reply_markup)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  # Create the keyboard layout
  keyboard = [
    [InlineKeyboardButton("ЛФИ", callback_data="ЛФИ")],
    [InlineKeyboardButton("ФПМИ", callback_data="ФПМИ")],
    [InlineKeyboardButton("ФРКТ", callback_data="ФРКТ")],
    [InlineKeyboardButton("ФБМФ", callback_data="ФБМФ")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  # Send the options menu to the user
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))

async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if context.args == []:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста используйте эту команду с аргументом:\n/contact <ваш текст>")
  else:
    await context.bot.send_message(chat_id=tg_config.creator_id, text="@"+update.effective_user.username+": "+" ".join(context.args))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Передали создателю все что вы написали") 
    

async def mipt_school(update, context):
  query = update.callback_query
  await query.answer()
  school_string = query.data
  keyboard = [
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 1 Курс', False) else CROSS_EMOJI} {school_string} 1 Курс", callback_data=f'{school_string} 1 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 2 Курс', False) else CROSS_EMOJI} {school_string} 2 Курс", callback_data=f'{school_string} 2 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 3 Курс', False) else CROSS_EMOJI} {school_string} 3 Курс", callback_data=f'{school_string} 3 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 4 Курс', False) else CROSS_EMOJI} {school_string} 4 Курс", callback_data=f'{school_string} 4 Курс')],
    [InlineKeyboardButton("Назад", callback_data='Меню')]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  # Send the options menu to the user
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_mipt_school(update, context):
  query = update.callback_query
  await query.answer()
  edit_string = query.data
  school_string = query.data.split(" ")[0]
  context.user_data[edit_string] = not context.user_data.get(edit_string, False)
  keyboard = [
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 1 Курс', False) else CROSS_EMOJI} {school_string} 1 Курс", callback_data=f'{school_string} 1 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 2 Курс', False) else CROSS_EMOJI} {school_string} 2 Курс", callback_data=f'{school_string} 2 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 3 Курс', False) else CROSS_EMOJI} {school_string} 3 Курс", callback_data=f'{school_string} 3 Курс')],
    [InlineKeyboardButton(f"{CHECKMARK_EMOJI if context.user_data.get(f'{school_string} 4 Курс', False) else CROSS_EMOJI} {school_string} 4 Курс", callback_data=f'{school_string} 4 Курс')],
    [InlineKeyboardButton("Назад", callback_data='Меню')],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  # Send the options menu to the user
  await query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))

#define a weird function
async def get_and_fetch_all(context):
    for group in groups.keys():
      if context.user_data.get(group, False):
        posts = vkmanager.get_new_posts(vk_id = groups[group])
        for post in reversed(posts):
          await context.bot.sendMessage(chat_id=context., text=post['text'])
          await sleep(1)

# Set up the Telegram bot
def main():
  application = ApplicationBuilder().token(tg_config.token).build()

  #наборы папок факультетов
  application.add_handler(CommandHandler('start', get_message))
  application.add_handler(CommandHandler('edit', get_message))
  application.add_handler(CommandHandler('new', new))
  application.add_handler(CommandHandler('contact', new))
  application.add_handler(CallbackQueryHandler(menu, pattern="^Меню$"))
  application.add_handler(CallbackQueryHandler(mipt_school, pattern="^ЛФИ$|^ФПМИ$|^ФРКТ$|^ФБМФ$"))
  application.add_handler(CallbackQueryHandler(edit_mipt_school))
  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
  main()

from flask import Flask
from flask import request
from threading import Thread
import time
import requests
from bot.logger import setup_logger

app = Flask('')
logger = setup_logger("alive")


@app.route('/')
def home():
  logger.info("just received a ping")
  return "I'm alive"


def run():
  app.run(host='0.0.0.0', port=255)


def keep_alive():
  logger.info("started keeping alive")
  t = Thread(target=run)
  t.start()

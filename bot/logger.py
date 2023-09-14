import logging
import os

def clear_logs():
  folder = os.path.join("logs")
  for filename in os.listdir(folder):
      file_path = os.path.join(folder, filename)
      try:
          if os.path.isfile(file_path) or os.path.islink(file_path):
              os.remove(file_path)
      except Exception as e:
          print('Failed to delete %s. Reason: %s' % (file_path, e))

def setup_logger(name):
  # Create a logger instance
  logger = logging.getLogger(name)
  logger.setLevel(logging.DEBUG)

  # Create a file handler and set its level to DEBUG
  file_handler = logging.FileHandler(os.path.join("logs", f"{name}.log"))
  file_handler.setLevel(logging.DEBUG)

  #create a all-in-one log:
  file_handler_2 = logging.FileHandler(os.path.join("logs", "all.log"))
  file_handler_2.setLevel(logging.DEBUG)

  #create a all-in-one log:
  file_handler_3 = logging.FileHandler(os.path.join("logs", "errors.log"))
  file_handler_3.setLevel(logging.DEBUG)

  # Create a stream handler and set its level to INFO
  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(logging.INFO)

  # Create a formatter and add it to the handlers
  formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  file_handler.setFormatter(formatter)
  file_handler_2.setFormatter(formatter)
  stream_handler.setFormatter(formatter)

  # Add the handlers to the logger
  logger.addHandler(file_handler)
  logger.addHandler(file_handler_2)
  logger.addHandler(stream_handler)

  return logger

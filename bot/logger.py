import logging, os.path


def setup_logger(name):
  # Create a logger instance
  logger = logging.getLogger(name)
  logger.setLevel(logging.DEBUG)

  # Create a file handler and set its level to DEBUG
  file_handler = logging.FileHandler(os.path.join("logs", f"{name}.log"), mode = "w")
  file_handler.setLevel(logging.DEBUG)

  #create a all-in-one log:
  file_handler_2 = logging.FileHandler(os.path.join("logs", "all.log"), mode = "w")
  file_handler_2.setLevel(logging.DEBUG)

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

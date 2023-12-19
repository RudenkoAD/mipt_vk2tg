import os
import dotenv
dotenv.load_dotenv()

TG_TOKEN = os.environ['TG_TOKEN']
TG_CREATOR_ID = os.environ['TG_CREATOR_ID']
VK_SERVICE_TOKEN = os.environ['VK_SERVICE_TOKEN']
VK_ACCESS_TOKEN = os.environ['VK_ACCESS_TOKEN']
VK_SECURE_KEY = os.environ['VK_SECURE_KEY']


class psql_config:
  dbname = os.environ['psql_dbname']
  user = os.environ['psql_user']
  password = os.environ['psql_password']
  host = os.environ['psql_host']
  tablename_users = os.environ['psql_tablename_users']
  tablename_links = os.environ['psql_tablename_links']
  tablename_groups = os.environ['psql_tablename_groups']

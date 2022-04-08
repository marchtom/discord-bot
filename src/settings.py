import os

from dotenv import load_dotenv
load_dotenv()

BOT_CALL = os.getenv('BOT_CALL')
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 5)) #s
MY_ID = int(os.getenv('MY_ID'))
SECRET = os.getenv('SECRET')
DB_URL = os.getenv('DB_URL')

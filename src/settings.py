import os

from dotenv import load_dotenv
load_dotenv()

BOT_CALL = '!magiczny-bot'
SLEEP_TIME = 5 #s
MY_ID = int(os.getenv('MY_ID'))
SECRET = os.getenv('SECRET')

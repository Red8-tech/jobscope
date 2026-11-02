import os

from dotenv import load_dotenv

from jobscope.api.app import create_app_from_env

load_dotenv()
app = create_app_from_env(os.environ)
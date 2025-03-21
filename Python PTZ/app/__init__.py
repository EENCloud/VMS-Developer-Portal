import logging
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

logging.basicConfig(level=logging.DEBUG)  # Enable DEBUG level for all logs
for handler in app.logger.handlers:
    logging.getLogger().addHandler(handler)

from app import routes

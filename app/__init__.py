__version__ = '0.1.0'

import hashlib
from enum import Enum

import redis
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_redis import FlaskRedis
from flask_session import Session
from os import environ, path

app = Flask(__name__)
bootstrap = Bootstrap(app)

app.config['SECRET_KEY'] = hashlib.sha256(b'very hard to guess string').digest()
app.config['REDIS_URL'] = environ['REDIS'] # "redis://:@172.17.0.3:6379/0"

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] =  redis.from_url(app.config['REDIS_URL'])

redis_client = FlaskRedis(app)
server_session = Session(app)

REDIS_TTL = 72000
# BASE_MP3_DIR = environ['MP3']

BASE_DIR = path.abspath(path.dirname(__file__))
MP3_DIR = path.join('static', 'mp3')
BASE_MP3_DIR = path.join(BASE_DIR, MP3_DIR)

def makkey(prefix='None', pid=0, subkey=None):
    return f'{prefix}:{str(pid)}:{subkey.value}'


class SUBKEYS(Enum):
    progress    = 'progress'
    status      = 'status'
    error       = 'error'
    critical    = 'critical'
    warning     = 'warning'
    files       = 'files'


subkeys = SUBKEYS

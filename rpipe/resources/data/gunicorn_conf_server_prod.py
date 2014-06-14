import os.path

user = 'www-data'
group = 'www-data'

debug = 'false'
daemon = 'true'

bind = 'unix:/tmp/rp_server.gunicorn.sock'

_LOG_PATH = '/var/log'
errorlog = os.path.join(_LOG_PATH, 'app_rpipe.log')
loglevel = 'info'
worker_class = 'gevent'

import os.path

user = 'www-data'
group = 'www-data'

debug = 'false'
daemon = 'false'

bind = 'unix:/tmp/rpclient.gunicorn.sock'

_LOG_PATH = '/var/log'
errorlog = os.path.join(_LOG_PATH, 'restpipe.log')
loglevel = 'warning'
worker_class = 'gevent'

timeout = 120

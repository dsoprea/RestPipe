debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rpclient.gunicorn.sock'

errorlog = '-'
loglevel = 'debug'
worker_class = 'gevent'

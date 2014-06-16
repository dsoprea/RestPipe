debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rpserver.gunicorn.sock'

errorlog = '-'
loglevel = 'debug'
worker_class = 'gevent'

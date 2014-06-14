debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rp_server.gunicorn.sock'

errorlog = '-'
loglevel = 'debug'
worker_class = 'gevent'

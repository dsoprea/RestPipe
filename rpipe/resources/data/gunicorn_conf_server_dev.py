debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rpserver.gunicorn.sock'

errorlog = '-'
loglevel = 'warning'
worker_class = 'gevent'

timeout = 300

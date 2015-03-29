import os.path

user = 'www-data'
group = 'www-data'

debug = 'false'
daemon = 'false'

bind = 'unix:/tmp/rpserver.gunicorn.sock'

errorlog = os.path.join('/var/log', 'restpipe.log')
loglevel = 'warning'
worker_class = 'gevent'

timeout = 120

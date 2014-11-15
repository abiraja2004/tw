uwsgi -s /tmp/uwsgi.sock -w application:app --chown-socket=www-data:www-data --catch-exceptions --logto /var/log/uwsgi/uwsgi.log

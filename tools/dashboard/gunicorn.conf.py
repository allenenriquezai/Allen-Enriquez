"""Gunicorn config for Enriquez OS Dashboard."""

bind = '0.0.0.0:5002'
workers = 2
worker_class = 'gthread'
threads = 4
timeout = 300  # long timeout for agent/API calls
accesslog = '-'
errorlog = '-'
loglevel = 'info'

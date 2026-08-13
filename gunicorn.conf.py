import os


default_host = os.environ.get("APP_HOST", "127.0.0.1")
bind = os.environ.get("GUNICORN_BIND", f"{default_host}:{os.environ.get('PORT', '5001')}")
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
capture_output = True
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
sendfile = False

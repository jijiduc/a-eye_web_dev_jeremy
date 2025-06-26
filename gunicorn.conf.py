# gunicorn.conf.py

# Server socket
bind = "0.0.0.0:5000"

# Worker settings
workers = 4  # Adjust based on CPU cores

# Request timeout (set very high, but not "unlimited" – see notes below)
timeout = 3600  # 1 hour

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
#!/bin/bash

# Activate virtual environment
. /home/nivenly/reversejobboard/bin/activate

# Start Gunicorn with 4 worker processes
#exec gunicorn -w 4 app:app --bind 127.0.0.1:8000 --access-logfile /var/log/gunicorn/access.log --error-logfile /var/log/gunicorn/error.log
exec gunicorn -w 4 app:app --bind 127.0.0.1:8000 


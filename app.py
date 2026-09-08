#!/usr/bin/env python
"""
ConstructSync Django Compatibility Entrypoint.
Enables running `python app.py` to start the Django development server seamlessly.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')

import django
django.setup()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    host = os.environ.get('HOST', '127.0.0.1')
    port = os.environ.get('PORT', '5000')
    print(f"Starting ConstructSync Django Server on http://{host}:{port} ...")
    sys.argv = ['manage.py', 'runserver', f'{host}:{port}']
    execute_from_command_line(sys.argv)
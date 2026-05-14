"""
WSGI entry point per PythonAnywhere.

Incollare il contenuto di questo file nel WSGI configuration file
raggiungibile dalla scheda Web > WSGI configuration file.
"""
import sys
import os

# Sostituire con il proprio username PythonAnywhere e il nome della cartella
PROJECT_HOME = "/home/TUOUSERNAME/Delpy_EDU"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.chdir(PROJECT_HOME)

from app import create_app

application = create_app()

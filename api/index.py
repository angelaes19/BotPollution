import sys
import os

# Añade el directorio raíz a sys.path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

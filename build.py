import PyInstaller.__main__
import os

# Création du dossier logs s'il n'existe pas
if not os.path.exists('logs'):
    os.makedirs('logs')

PyInstaller.__main__.run([
    'app.py',
    '--onefile',
    '--name=cashdrawer_service',
    '--add-data=logs;logs',  # Inclure le dossier logs
    '--hidden-import=escpos.printer',
    '--hidden-import=usb.core',
    '--hidden-import=usb.util',
    '--noconsole',  # Pas de console en arrière-plan
])

import PyInstaller.__main__
import os
import configparser
import shutil

# Création du dossier logs s'il n'existe pas
if not os.path.exists('logs'):
    os.makedirs('logs')

# Vérification de l'existence du fichier config.ini
if not os.path.exists('config.ini'):
    print("Le fichier config.ini n'existe pas. Création d'un fichier de configuration par défaut...")
    config = configparser.ConfigParser()
    config['printer'] = {'name': 'TICKET'}
    config['cashdrawer'] = {'command': '1b70001afa'}
    config['invoice_printer'] = {
        'autoprint': 'true',
        'name': 'FACTURE',
        'download_folder': 'C:\\Users\\Public\\Downloads',
        'scan_frequency': '5',
        'open_delay': '10',
        'purge_on_start': 'true',
        'file_extensions': '.pdf'
    }
    config['server'] = {'port': '22548', 'host': '0.0.0.0'}
    config['logs'] = {'folder': 'logs', 'filename': 'cashdrawer.log', 'retention_days': '30'}
    
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    print("Fichier config.ini créé avec succès.")

# Vérification et création des dossiers nécessaires
if not os.path.exists('templates'):
    print("Dossier templates non trouvé, création du dossier...")
    os.makedirs('templates', exist_ok=True)

if not os.path.exists('static'):
    print("Dossier static non trouvé, création du dossier...")
    os.makedirs('static', exist_ok=True)

# Exécution de PyInstaller
PyInstaller.__main__.run([
    'app.py',
    '--onefile',
    '--name=cashdrawer_service',
    '--add-data=logs;logs',  # Inclure le dossier logs
    '--add-data=config.ini;.',  # Inclure le fichier de configuration
    '--add-data=templates;templates',  # Inclure le dossier templates
    '--add-data=static;static',  # Inclure le dossier static
    '--hidden-import=escpos.printer',
    '--hidden-import=usb.core',
    '--hidden-import=usb.util',
    '--hidden-import=bcrypt',  # Ajouter bcrypt comme import caché
    '--hidden-import=win32print',  # Ajouter win32print comme import caché
    '--hidden-import=win32ui',  # Ajouter win32ui comme import caché
    '--hidden-import=win32api',  # Ajouter win32api comme import caché
    '--noconsole',  # Pas de console en arrière-plan
])

# Copier le fichier config.ini dans le dossier dist comme modèle
print("Copie du fichier config.ini dans le dossier dist comme modèle...")
if not os.path.exists('dist'):
    os.makedirs('dist')
shutil.copy2('config.ini', 'dist/config.ini')
print("Fichier config.ini copié avec succès.")

# Créer un fichier README.txt dans le dossier dist pour expliquer comment utiliser l'application
readme_content = """Service Tiroir-Caisse pour Odoo POS
====================================

Ce service permet d'ouvrir le tiroir-caisse et d'imprimer des factures depuis Odoo POS.

Configuration:
-------------
1. Accédez à l'interface de configuration via http://localhost:22548/config
2. Lors de la première utilisation, vous devrez créer un mot de passe
3. Configurez les paramètres selon vos besoins

Logs:
-----
Les logs sont stockés dans le dossier 'C:\\ProgramData\\OdooPOS\\logs'.
Si vous rencontrez des problèmes, consultez ces logs pour plus d'informations.

Note importante:
---------------
Le fichier config.ini est stocké dans 'C:\\ProgramData\\OdooPOS\\config.ini' et contient vos paramètres.
Ce dossier est utilisé pour éviter les problèmes de permissions sous Windows.
"""

with open('dist/README.txt', 'w') as readme_file:
    readme_file.write(readme_content)
print("Fichier README.txt créé avec succès.")

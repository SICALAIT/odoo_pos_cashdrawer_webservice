from flask import Flask, jsonify, send_file, request, render_template, redirect, url_for, flash, session
import win32print
import win32ui
import win32api
import logging
import bcrypt
import secrets
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
import os
import platform
import configparser
import binascii
import threading
import time
import glob
import shutil
import sys
from werkzeug.serving import WSGIRequestHandler

# Version du service
VERSION = "1.0.0"

# Fonction pour déterminer si l'application est exécutée à partir d'un exécutable PyInstaller
def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Fonction pour obtenir le chemin correct des ressources
def resource_path(relative_path):
    if is_bundled():
        # Si l'application est exécutée à partir d'un exécutable PyInstaller
        base_path = sys._MEIPASS
    else:
        # Si l'application est exécutée normalement
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Chargement de la configuration
config = configparser.ConfigParser()

# Déterminer le chemin du fichier config.ini
if is_bundled():
    # Si l'application est exécutée depuis un exécutable
    if platform.system() == 'Windows':
        # Sous Windows, utiliser le dossier ProgramData
        program_data_dir = os.path.join('C:\\', 'ProgramData', 'OdooPOS')
        # S'assurer que le dossier existe
        try:
            if not os.path.exists(program_data_dir):
                os.makedirs(program_data_dir, exist_ok=True)
                print(f"Dossier de configuration créé: {program_data_dir}")
            
            # Créer aussi le dossier logs à l'avance
            logs_dir = os.path.join(program_data_dir, 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir, exist_ok=True)
                print(f"Dossier de logs créé: {logs_dir}")
                
            config_path = os.path.join(program_data_dir, 'config.ini')
            print(f"Mode exécutable Windows détecté, fichier de configuration: {config_path}")
        except Exception as e:
            print(f"Erreur lors de la création des dossiers: {str(e)}")
            # Fallback au dossier de l'exécutable en cas d'erreur
            executable_dir = os.path.dirname(sys.executable)
            config_path = os.path.join(executable_dir, 'config.ini')
            print(f"Utilisation du dossier de l'exécutable comme fallback: {config_path}")
    else:
        # Pour les autres systèmes, utiliser le dossier à côté de l'exécutable
        executable_dir = os.path.dirname(sys.executable)
        config_path = os.path.join(executable_dir, 'config.ini')
        print(f"Mode exécutable détecté, fichier de configuration: {config_path}")
else:
    # Si l'application est exécutée normalement, utiliser le fichier config.ini dans le répertoire courant
    config_path = 'config.ini'
    print(f"Mode normal, fichier de configuration: {config_path}")

try:
    # Vérifier si le fichier config.ini existe
    if os.path.exists(config_path):
        config.read(config_path)
        print(f"Fichier de configuration lu avec succès: {config_path}")
        
        # Vérifier si la section [auth] existe, sinon l'ajouter
        if 'auth' not in config:
            print("Section [auth] manquante dans le fichier de configuration. Ajout de la section...")
            config['auth'] = {
                'password_hash': '',
                'salt': ''
            }
            # Sauvegarder le fichier mis à jour
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            print(f"Section [auth] ajoutée au fichier de configuration: {config_path}")
    else:
        # Si le fichier n'existe pas, vérifier s'il y a un fichier config.ini dans le dossier de l'exécutable
        # (pour le cas où l'application est exécutée depuis un exécutable Windows)
        default_config_found = False
        
        if is_bundled() and platform.system() == 'Windows':
            executable_dir = os.path.dirname(sys.executable)
            default_config_path = os.path.join(executable_dir, 'config.ini')
            
            if os.path.exists(default_config_path):
                print(f"Fichier de configuration par défaut trouvé: {default_config_path}")
                try:
                    # Copier le fichier de configuration par défaut vers le dossier ProgramData
                    shutil.copy2(default_config_path, config_path)
                    print(f"Fichier de configuration copié vers: {config_path}")
                    config.read(config_path)
                    default_config_found = True
                except Exception as e:
                    print(f"Erreur lors de la copie du fichier de configuration: {str(e)}")
        
        # Si aucun fichier de configuration n'a été trouvé ou copié, créer un nouveau fichier
        if not default_config_found:
            print(f"Fichier de configuration introuvable: {config_path}")
            print("Utilisation des valeurs par défaut et création du fichier...")
            config['auth'] = {
                'password_hash': '',
                'salt': ''
            }
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
            
            # Sauvegarder le fichier de configuration
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            print(f"Fichier de configuration créé avec succès: {config_path}")
except Exception as e:
    print(f"Erreur lors de la lecture/écriture du fichier de configuration: {str(e)}")
    # Utiliser les valeurs par défaut en mémoire sans sauvegarder le fichier
    config['auth'] = {
        'password_hash': '',
        'salt': ''
    }
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

# Configuration du logging
log_folder = config.get('logs', 'folder', fallback='logs')

# Si l'application est exécutée depuis un exécutable, utiliser un chemin absolu pour les logs
if is_bundled():
    if platform.system() == 'Windows':
        # Sous Windows, utiliser le dossier ProgramData pour les logs
        program_data_dir = os.path.join('C:\\', 'ProgramData', 'OdooPOS')
        log_folder = os.path.join(program_data_dir, log_folder)
        print(f"Mode exécutable Windows détecté, dossier de logs: {log_folder}")
    else:
        # Pour les autres systèmes, utiliser le dossier à côté de l'exécutable
        executable_dir = os.path.dirname(sys.executable)
        log_folder = os.path.join(executable_dir, log_folder)
        print(f"Mode exécutable détecté, dossier de logs: {log_folder}")

try:
    if not os.path.exists(log_folder):
        os.makedirs(log_folder, exist_ok=True)
        print(f"Dossier de logs créé: {log_folder}")
except Exception as e:
    print(f"Erreur lors de la création du dossier de logs: {str(e)}")

# Configuration du logger avec rotation
log_filename = config.get('logs', 'filename', fallback='cashdrawer.log')
log_file = os.path.join(log_folder, log_filename)
retention_days = int(config.get('logs', 'retention_days', fallback='30'))

# Création du logger
logger = logging.getLogger('cashdrawer')
logger.setLevel(logging.INFO)

# Dictionnaire pour suivre les erreurs déjà enregistrées
error_cache = {}
# Fonction pour éviter de répéter les mêmes erreurs dans les logs
def log_error_once(message, error_type="general"):
    """Enregistre une erreur une seule fois jusqu'à ce qu'elle soit résolue"""
    error_key = f"{error_type}:{message}"
    if error_key not in error_cache:
        logger.error(message)
        error_cache[error_key] = True
        return True
    return False

# Vérification si le logger a déjà des handlers pour éviter les doublons
if not logger.handlers:
    try:
        # Handler pour fichier avec rotation
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=retention_days
        )
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        print(f"Handler de fichier configuré: {log_file}")
        
        # Ajout d'un handler console pour voir les logs en temps réel
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        print("Handler console configuré")
    except Exception as e:
        print(f"Erreur lors de la configuration des handlers de log: {str(e)}")

# Initialisation de l'application Flask avec les chemins corrects pour les templates et les fichiers statiques
if is_bundled():
    template_folder = resource_path('templates')
    static_folder = resource_path('static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    logger.info(f"Application exécutée depuis un exécutable. Templates: {template_folder}, Static: {static_folder}")
else:
    app = Flask(__name__)
    logger.info("Application exécutée en mode normal.")

# Configuration de la clé secrète pour les sessions Flask
app.secret_key = secrets.token_hex(16)  # Génère une clé secrète aléatoire
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Fonctions d'authentification
def is_first_setup():
    """Vérifie si c'est la première configuration (pas de mot de passe défini)"""
    return not config.get('auth', 'password_hash', fallback='').strip()

def verify_password(password):
    """Vérifie si le mot de passe est correct"""
    if is_first_setup():
        return False
    
    stored_hash = config.get('auth', 'password_hash', fallback='')
    stored_salt = config.get('auth', 'salt', fallback='')
    
    if not stored_hash or not stored_salt:
        return False
    
    try:
        # Convertir le sel stocké en bytes
        salt = stored_salt.encode('utf-8')
        # Hacher le mot de passe fourni avec le sel stocké
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        # Comparer avec le hash stocké
        return hashed.decode('utf-8') == stored_hash
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe: {str(e)}")
        return False

def set_password(password):
    """Définit un nouveau mot de passe"""
    try:
        # Générer un nouveau sel
        salt = bcrypt.gensalt()
        # Hacher le mot de passe avec le sel
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Stocker le hash et le sel dans la configuration
        config['auth']['password_hash'] = hashed.decode('utf-8')
        config['auth']['salt'] = salt.decode('utf-8')
        
        # Sauvegarder la configuration
        # Utiliser le même chemin que celui utilisé pour charger la configuration
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        
        logger.info(f"Nouveau mot de passe défini avec succès dans {config_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la définition du mot de passe: {str(e)}")
        return False

def is_authenticated():
    """Vérifie si l'utilisateur est authentifié"""
    return session.get('authenticated', False)

def login_required(f):
    """Décorateur pour protéger les routes qui nécessitent une authentification"""
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash("Vous devez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('config_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def is_local_request():
    """Vérifie si la requête vient de localhost"""
    return request.remote_addr in ['127.0.0.1', 'localhost']

# Commande ESC/POS pour ouvrir le tiroir-caisse depuis la configuration
drawer_cmd_hex = config.get('cashdrawer', 'command', fallback='1b70001afa')
try:
    OPEN_DRAWER_CMD = binascii.unhexlify(drawer_cmd_hex)
except Exception as e:
    log_error_once(f"Erreur lors de la conversion de la commande du tiroir-caisse: {str(e)}", "drawer_cmd_conversion_error")
    # Valeur par défaut si la conversion échoue
    OPEN_DRAWER_CMD = b'\x1b\x70\x00\x19\xfa'

def open_cashdrawer():
    try:
        if platform.system() == 'Windows':
            printer_name = config.get('printer', 'name', fallback='TICKET')  # Nom de l'imprimante depuis la configuration
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                # Démarrage du document d'impression
                job = win32print.StartDocPrinter(printer_handle, 1, ("Open Cash Drawer", None, "RAW"))
                win32print.StartPagePrinter(printer_handle)
                # Envoyer la commande ESC/POS pour ouvrir le tiroir
                win32print.WritePrinter(printer_handle, OPEN_DRAWER_CMD)
                win32print.EndPagePrinter(printer_handle)
                win32print.EndDocPrinter(printer_handle)
                return True
            finally:
                win32print.ClosePrinter(printer_handle)
        else:
            log_error_once("Ce service n'est compatible qu'avec Windows", "os_not_windows")
            return False
    except Exception as e:
        log_error_once(f"Erreur lors de l'ouverture du tiroir: {str(e)}", "open_drawer_error")
        return False

@app.route('/open-cash-drawer', methods=['GET'])
def open_drawer():
    # Vérification que la requête vient de localhost
    if not is_local_request():
        log_error_once(f"Tentative d'accès distant à l'ouverture du tiroir depuis {request.remote_addr}", "remote_access_drawer")
        return jsonify({"status": "error", "message": "Accès refusé - Local uniquement"}), 403

    try:
        success = open_cashdrawer()
        if success:
            logger.info("Tiroir-caisse ouvert avec succès")
            return jsonify({"status": "success", "message": "Tiroir-caisse ouvert"}), 200
        else:
            return jsonify({"status": "error", "message": "Erreur lors de l'ouverture du tiroir"}), 500
    except Exception as e:
        log_error_once(f"Erreur serveur: {str(e)}", "server_error")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "running",
        "message": "Service actif",
        "remote_addr": request.remote_addr,
        "scheme": request.scheme
    }), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """Endpoint pour récupérer le fichier de logs"""
    try:
        # Vérification que le fichier de logs existe
        if not os.path.exists(log_file):
            log_error_once(f"Fichier de logs introuvable: {log_file}", "logs_file_not_found")
            return jsonify({"status": "error", "message": f"Fichier de logs introuvable: {log_file}"}), 404
            
        # Vérification des permissions
        if not os.access(log_file, os.R_OK):
            log_error_once(f"Permissions insuffisantes pour lire le fichier de logs: {log_file}", "logs_file_permission")
            return jsonify({"status": "error", "message": "Permissions insuffisantes pour accéder aux logs"}), 403
            
        logger.info(f"Téléchargement des logs depuis {request.remote_addr}")
        return send_file(log_file, as_attachment=True, download_name='cashdrawer.log')
    except Exception as e:
        log_error_once(f"Erreur lors de l'accès aux logs: {str(e)}", "logs_access_error")
        return jsonify({"status": "error", "message": f"Impossible d'accéder aux logs: {str(e)}"}), 500

@app.route('/logs/purge', methods=['GET'])
@login_required
def purge_logs():
    """Endpoint pour purger les logs"""
    try:
        # Vérification que le fichier de logs existe
        if os.path.exists(log_file):
            # Fermer tous les handlers de logs pour libérer le fichier
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            # Supprimer le fichier de logs
            os.remove(log_file)
            
            # Supprimer les fichiers de logs rotés
            log_dir = os.path.dirname(log_file)
            log_basename = os.path.basename(log_file)
            for f in os.listdir(log_dir):
                if f.startswith(log_basename) and f != log_basename:
                    try:
                        os.remove(os.path.join(log_dir, f))
                    except Exception as e:
                        print(f"Erreur lors de la suppression du fichier de log roté {f}: {str(e)}")
            
            # Recréer les handlers de logs
            try:
                # Handler pour fichier avec rotation
                file_handler = TimedRotatingFileHandler(
                    log_file,
                    when="midnight",
                    interval=1,
                    backupCount=retention_days
                )
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(file_handler)
                
                # Ajout d'un handler console pour voir les logs en temps réel
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(console_handler)
            except Exception as e:
                print(f"Erreur lors de la reconfiguration des handlers de log: {str(e)}")
            
            # Log de l'action
            logger.info("Logs purgés avec succès")
            
            return jsonify({
                "status": "success",
                "message": "Logs purgés avec succès"
            }), 200
        else:
            return jsonify({
                "status": "success",
                "message": "Aucun fichier de logs à purger"
            }), 200
    except Exception as e:
        error_msg = f"Erreur lors de la purge des logs: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

# Fonction pour ouvrir un fichier PDF avec le lecteur par défaut
def print_pdf_file(file_path, printer_name):
    try:
        logger.info(f"Tentative d'ouverture du fichier: {file_path} (au lieu de l'impression sur {printer_name})")
        
        # Normalisation du chemin Windows
        if file_path.startswith('C:/'):
            file_path = file_path.replace('/', '\\')
            logger.info(f"Normalisation du chemin Windows du fichier: {file_path}")
        
        # Vérification que le fichier existe
        if not os.path.exists(file_path):
            log_error_once(f"Fichier introuvable: {file_path}", f"file_not_found_{file_path}")
            return False
            
        # Vérification des permissions
        if not os.access(file_path, os.R_OK):
            log_error_once(f"Permissions insuffisantes pour lire le fichier: {file_path}", f"file_permission_{file_path}")
            return False
            
        if platform.system() == 'Windows':
            # Méthode 1: Utiliser os.startfile (méthode native Windows)
            try:
                logger.info(f"Tentative d'ouverture avec os.startfile")
                os.startfile(file_path)
                logger.info(f"Fichier {file_path} ouvert avec os.startfile")
                return True
            except Exception as e1:
                logger.warning(f"Échec de l'ouverture avec os.startfile: {str(e1)}")
                
                # Méthode 2: Utiliser subprocess.Popen
                try:
                    import subprocess
                    logger.info(f"Tentative d'ouverture avec subprocess.Popen")
                    subprocess.Popen(['start', '', file_path], shell=True)
                    logger.info(f"Fichier {file_path} ouvert avec subprocess.Popen")
                    return True
                except Exception as e2:
                    logger.warning(f"Échec de l'ouverture avec subprocess.Popen: {str(e2)}")
                    
                    # Méthode 3: Utiliser win32api.ShellExecute comme dernier recours
                    try:
                        logger.info(f"Tentative d'ouverture avec win32api.ShellExecute")
                        win32api.ShellExecute(
                            0,
                            "open",
                            file_path,
                            None,
                            ".",
                            1  # SW_SHOWNORMAL - Afficher la fenêtre normalement
                        )
                        logger.info(f"Fichier {file_path} ouvert avec win32api.ShellExecute")
                        return True
                    except Exception as e3:
                        log_error_once(f"Échec de toutes les méthodes d'ouverture pour {file_path}: {str(e3)}", f"open_file_error_{file_path}")
                        return False
        else:
            log_error_once(f"Ce service n'est compatible qu'avec Windows. Système détecté: {platform.system()}", "open_os_not_windows")
            return False
    except Exception as e:
        log_error_once(f"Erreur lors de l'ouverture du fichier {file_path}: {str(e)}", f"open_file_error_{file_path}")
        return False

# Fonction pour purger un dossier
def purge_folder(folder_path, extensions):
    try:
        logger.info(f"Tentative de purge du dossier: {folder_path} pour les extensions: {extensions}")
        
        # Normalisation du chemin Windows
        if folder_path.startswith('C:/'):
            folder_path = folder_path.replace('/', '\\')
            logger.info(f"Normalisation du chemin Windows du dossier: {folder_path}")
        
        # Vérification que le dossier existe
        if not os.path.exists(folder_path):
            log_error_once(f"Dossier introuvable: {folder_path}", f"folder_not_found_{folder_path}")
            return False
            
        # Vérification des permissions
        if not os.access(folder_path, os.R_OK | os.W_OK):
            log_error_once(f"Permissions insuffisantes pour accéder au dossier: {folder_path}", f"folder_permission_{folder_path}")
            return False
            
        count = 0
        for ext in extensions:
            logger.debug(f"Recherche des fichiers avec extension: {ext}")
            files = glob.glob(os.path.join(folder_path, f"*{ext}"))
            logger.info(f"Nombre de fichiers trouvés avec extension {ext}: {len(files)}")
            
            for file in files:
                try:
                    logger.debug(f"Tentative de suppression du fichier: {file}")
                    os.remove(file)
                    logger.info(f"Fichier supprimé: {file}")
                    count += 1
                except Exception as e:
                    log_error_once(f"Erreur lors de la suppression du fichier {file}: {str(e)}", f"purge_error_{file}")
                    
        logger.info(f"Purge du dossier {folder_path}: {count} fichiers supprimés")
        return True
    except Exception as e:
        log_error_once(f"Erreur lors de la purge du dossier {folder_path}: {str(e)}", f"purge_folder_error_{folder_path}")
        return False

# Fonction pour scanner le dossier de téléchargement et imprimer les PDF
def scan_and_print_pdfs():
    logger.info("Démarrage de la fonction scan_and_print_pdfs")
    
    # Récupération des paramètres de configuration
    printer_name = config.get('invoice_printer', 'name', fallback='FACTURE')
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
    
    # Normalisation du chemin Windows
    if download_folder.startswith('C:/'):
        # Remplacer les slashes par des backslashes
        download_folder = download_folder.replace('/', '\\')
        logger.info(f"Normalisation du chemin Windows: {download_folder}")
    
    scan_frequency = int(config.get('invoice_printer', 'scan_frequency', fallback='5'))
    purge_on_start = config.getboolean('invoice_printer', 'purge_on_start', fallback=True)
    file_extensions_str = config.get('invoice_printer', 'file_extensions', fallback='.pdf')
    file_extensions = [ext.strip() for ext in file_extensions_str.split(',')]
    
    logger.info(f"Configuration: printer_name={printer_name}, download_folder={download_folder}, " +
                f"scan_frequency={scan_frequency}, purge_on_start={purge_on_start}, " +
                f"file_extensions={file_extensions}")
    
    # Vérification que le dossier existe
    if not os.path.exists(download_folder):
        try:
            os.makedirs(download_folder, exist_ok=True)
            logger.info(f"Dossier {download_folder} créé avec succès")
        except Exception as e:
            log_error_once(f"Erreur lors de la création du dossier {download_folder}: {str(e)}", f"create_folder_error_{download_folder}")
            return
    
    # Vérification des permissions du dossier
    if not os.access(download_folder, os.R_OK | os.W_OK):
        log_error_once(f"Permissions insuffisantes pour accéder au dossier: {download_folder}", f"scan_folder_permission_{download_folder}")
        return
    
    # Purge du dossier au premier lancement si configuré
    if purge_on_start:
        logger.info(f"Purge du dossier au démarrage: {download_folder}")
        purge_result = purge_folder(download_folder, file_extensions)
        logger.info(f"Résultat de la purge: {purge_result}")
    
    logger.info(f"Démarrage du scanner d'impression pour {printer_name} dans {download_folder}")
    
    # Compteurs pour les statistiques
    scan_count = 0
    print_success_count = 0
    print_fail_count = 0
    delete_success_count = 0
    delete_fail_count = 0
    
    # Boucle principale de scan
    while True:
        try:
            scan_count += 1
            # Log de scan uniquement en mode debug pour éviter de surcharger les logs
            logger.debug(f"Scan #{scan_count} du dossier {download_folder}")
            
            files_found = False
            for ext in file_extensions:
                files = glob.glob(os.path.join(download_folder, f"*{ext}"))
                
                if files:
                    files_found = True
                    logger.info(f"Fichiers trouvés avec extension {ext}: {len(files)}")
                    
                    for file in files:
                        logger.info(f"Traitement du fichier: {file}")
                        
                        # Ouverture du fichier
                        success = print_pdf_file(file, printer_name)
                        
                        if success:
                            print_success_count += 1
                            logger.info(f"Ouverture réussie: {file} (Total réussi: {print_success_count})")
                            
                            # Attendre que le lecteur PDF ait le temps de se lancer et de charger le fichier
                            # Délai configurable dans la section invoice_printer
                            open_delay = int(config.get('invoice_printer', 'open_delay', fallback='10'))
                            logger.info(f"Attente de {open_delay} secondes avant suppression du fichier...")
                            time.sleep(open_delay)
                            
                            # Suppression du fichier après ouverture
                            try:
                                os.remove(file)
                                delete_success_count += 1
                                logger.info(f"Fichier {file} supprimé après ouverture (Total supprimé: {delete_success_count})")
                            except Exception as e:
                                delete_fail_count += 1
                                log_error_once(f"Erreur lors de la suppression du fichier {file}: {str(e)}", f"delete_error_{file}")
                        else:
                            print_fail_count += 1
                            log_error_once(f"Échec de l'impression: {file}", f"print_error_{file}")
            
            # Ne pas logger les scans sans fichiers pour éviter de surcharger les logs
            
            # Statistiques périodiques (tous les 100 scans au lieu de 10)
            if scan_count % 100 == 0:
                logger.info(f"Statistiques après {scan_count} scans: " +
                           f"Impressions réussies: {print_success_count}, " +
                           f"Impressions échouées: {print_fail_count}, " +
                           f"Suppressions réussies: {delete_success_count}, " +
                           f"Suppressions échouées: {delete_fail_count}")
            
            # Attente avant le prochain scan
            logger.debug(f"Attente de {scan_frequency} secondes avant le prochain scan")
            time.sleep(scan_frequency)
        except Exception as e:
            # Utiliser la fonction log_error_once pour éviter de répéter la même erreur
            if log_error_once(f"Erreur lors du scan du dossier {download_folder}: {str(e)}", "scan_error"):
                logger.info(f"Reprise du scan dans {scan_frequency} secondes")
            time.sleep(scan_frequency)

@app.route('/invoice-printer/status', methods=['GET'])
def invoice_printer_status():
    """Endpoint pour vérifier le statut de l'imprimante facture"""
    autoprint_enabled = config.getboolean('invoice_printer', 'autoprint', fallback=True)
    printer_name = config.get('invoice_printer', 'name', fallback='FACTURE')
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
    
    # Normalisation du chemin Windows pour l'affichage
    if download_folder.startswith('C:/'):
        download_folder = download_folder.replace('/', '\\')
        
    scan_frequency = config.get('invoice_printer', 'scan_frequency', fallback='5')
    
    return jsonify({
        "status": "running",
        "autoprint": "enabled" if autoprint_enabled else "disabled",
        "printer_name": printer_name,
        "download_folder": download_folder,
        "scan_frequency": scan_frequency,
        "remote_addr": request.remote_addr,
        "scheme": request.scheme
    }), 200

# Routes pour la configuration
@app.route('/config', methods=['GET'])
def config_page():
    """Page de configuration principale"""
    # Vérifier si l'utilisateur est authentifié
    if not is_authenticated():
        return redirect(url_for('config_login'))
    
    # Informations système pour l'affichage
    system_info = f"{platform.system()} {platform.release()}"
    
    return render_template('config.html', config=config, system_info=system_info, version=VERSION)

@app.route('/config/login', methods=['GET', 'POST'])
def config_login():
    """Page de connexion"""
    first_setup = is_first_setup()
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        if first_setup:
            # Premier accès, création du mot de passe
            confirm_password = request.form.get('confirm_password')
            
            if not password or not confirm_password:
                flash("Veuillez remplir tous les champs.", "error")
                return render_template('login.html', first_setup=first_setup)
            
            if password != confirm_password:
                flash("Les mots de passe ne correspondent pas.", "error")
                return render_template('login.html', first_setup=first_setup)
            
            if len(password) < 6:
                flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
                return render_template('login.html', first_setup=first_setup)
            
            if set_password(password):
                session['authenticated'] = True
                flash("Mot de passe créé avec succès.", "success")
                return redirect(url_for('config_page'))
            else:
                flash("Erreur lors de la création du mot de passe.", "error")
                return render_template('login.html', first_setup=first_setup)
        else:
            # Vérification du mot de passe existant
            if verify_password(password):
                session['authenticated'] = True
                return redirect(url_for('config_page'))
            else:
                flash("Mot de passe incorrect.", "error")
                return render_template('login.html', first_setup=first_setup)
    
    return render_template('login.html', first_setup=first_setup)

@app.route('/config/logout', methods=['GET'])
def config_logout():
    """Déconnexion"""
    session.pop('authenticated', None)
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('config_login'))

@app.route('/config/save', methods=['POST'])
@login_required
def config_save():
    """Sauvegarde des modifications de la configuration"""
    try:
        # Mise à jour de la configuration du tiroir-caisse
        config['printer']['name'] = request.form.get('printer_name', 'TICKET')
        config['cashdrawer']['command'] = request.form.get('drawer_command', '1b70001afa')
        
        # Mise à jour de la configuration de l'imprimante facture
        config['invoice_printer']['autoprint'] = 'true' if request.form.get('autoprint') else 'false'
        config['invoice_printer']['name'] = request.form.get('invoice_printer_name', 'FACTURE')
        config['invoice_printer']['download_folder'] = request.form.get('download_folder', 'C:\\Users\\Public\\Downloads')
        config['invoice_printer']['scan_frequency'] = request.form.get('scan_frequency', '5')
        config['invoice_printer']['open_delay'] = request.form.get('open_delay', '10')
        config['invoice_printer']['purge_on_start'] = 'true' if request.form.get('purge_on_start') else 'false'
        config['invoice_printer']['file_extensions'] = request.form.get('file_extensions', '.pdf')
        
        # Mise à jour de la configuration du serveur
        config['server']['port'] = request.form.get('port', '22548')
        config['server']['host'] = request.form.get('host', '0.0.0.0')
        
        # Mise à jour de la configuration des logs
        config['logs']['folder'] = request.form.get('log_folder', 'logs')
        config['logs']['filename'] = request.form.get('log_filename', 'cashdrawer.log')
        config['logs']['retention_days'] = request.form.get('retention_days', '30')
        
        # Gestion du changement de mot de passe
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_new_password = request.form.get('confirm_new_password', '')
        
        if current_password and new_password and confirm_new_password:
            if not verify_password(current_password):
                flash("Mot de passe actuel incorrect.", "error")
                return redirect(url_for('config_page'))
            
            if new_password != confirm_new_password:
                flash("Les nouveaux mots de passe ne correspondent pas.", "error")
                return redirect(url_for('config_page'))
            
            if len(new_password) < 6:
                flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "error")
                return redirect(url_for('config_page'))
            
            if not set_password(new_password):
                flash("Erreur lors de la modification du mot de passe.", "error")
                return redirect(url_for('config_page'))
            
            flash("Mot de passe modifié avec succès.", "success")
        
        # Sauvegarde de la configuration
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        
        # Rechargement de la commande du tiroir-caisse
        global OPEN_DRAWER_CMD
        drawer_cmd_hex = config.get('cashdrawer', 'command', fallback='1b70001afa')
        try:
            OPEN_DRAWER_CMD = binascii.unhexlify(drawer_cmd_hex)
        except Exception as e:
            log_error_once(f"Erreur lors de la conversion de la commande du tiroir-caisse: {str(e)}", "drawer_cmd_conversion_error")
        
        flash("Configuration enregistrée avec succès.", "success")
        logger.info("Configuration modifiée via l'interface web")
        
        return redirect(url_for('config_page'))
    except Exception as e:
        flash(f"Erreur lors de l'enregistrement de la configuration: {str(e)}", "error")
        logger.error(f"Erreur lors de l'enregistrement de la configuration: {str(e)}")
        return redirect(url_for('config_page'))

@app.route('/invoice-printer/purge', methods=['GET'])
def invoice_printer_purge():
    """Endpoint pour purger le dossier de téléchargement"""
    # Vérification que la requête vient de localhost
    if not is_local_request():
        log_error_once(f"Tentative d'accès distant à la purge du dossier depuis {request.remote_addr}", "remote_access_purge")
        return jsonify({"status": "error", "message": "Accès refusé - Local uniquement"}), 403
    
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
    
    # Normalisation du chemin Windows
    if download_folder.startswith('C:/'):
        download_folder = download_folder.replace('/', '\\')
        logger.info(f"Normalisation du chemin Windows pour la purge: {download_folder}")
        
    file_extensions_str = config.get('invoice_printer', 'file_extensions', fallback='.pdf')
    file_extensions = [ext.strip() for ext in file_extensions_str.split(',')]
    
    success = purge_folder(download_folder, file_extensions)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"Dossier {download_folder} purgé avec succès"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la purge du dossier {download_folder}"
        }), 500

if __name__ == '__main__':
    print(f"Démarrage du service tiroir-caisse v{VERSION}")
    logger.info(f"Démarrage du service tiroir-caisse v{VERSION}")
    
    # Affichage des informations système
    system_info = f"Système d'exploitation: {platform.system()} {platform.release()}"
    print(system_info)
    logger.info(system_info)
    
    # Affichage du chemin du dossier de logs
    log_info = f"Dossier de logs: {os.path.abspath(log_folder)}, Fichier: {log_file}"
    print(log_info)
    logger.info(log_info)
    
    try:
        # Vérification si l'impression automatique est activée
        autoprint_enabled = config.getboolean('invoice_printer', 'autoprint', fallback=True)
        
        if autoprint_enabled:
            logger.info("Impression automatique activée dans la configuration")
            
            # Démarrage du thread de scan des PDF
            pdf_scanner_thread = threading.Thread(target=scan_and_print_pdfs, daemon=True)
            pdf_scanner_thread.start()
            logger.info("Thread de scan des PDF démarré")
        else:
            logger.info("Impression automatique désactivée dans la configuration")
        
        # Configuration pour supporter HTTP et HTTPS
        WSGIRequestHandler.protocol_version = "HTTP/1.1"  # Support HTTPS redirect
        
        # Écoute sur toutes les interfaces et accepte HTTP/HTTPS
        host = config.get('server', 'host', fallback='0.0.0.0')
        port = int(config.get('server', 'port', fallback='22548'))
        
        logger.info(f"Démarrage du serveur web sur {host}:{port}")
        
        app.run(
            host=host, 
            port=port,
            ssl_context=None,  # Permet les requêtes HTTP et HTTPS
            debug=False
        )
        
    except Exception as e:
        error_msg = f"Erreur lors du démarrage du service: {str(e)}"
        print(error_msg)
        log_error_once(error_msg, "startup_error")

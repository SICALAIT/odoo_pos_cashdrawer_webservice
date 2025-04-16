from flask import Flask, jsonify, send_file, request
import win32print
import win32ui
import win32api
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os
import platform
import configparser
import binascii
import threading
import time
import glob
import shutil
from werkzeug.serving import WSGIRequestHandler

# Chargement de la configuration
config = configparser.ConfigParser()
try:
    config.read('config.ini')
except Exception as e:
    print(f"Erreur lors de la lecture du fichier de configuration: {str(e)}")
    # Valeurs par défaut si le fichier de configuration n'existe pas
    config['printer'] = {'name': 'TICKET'}
    config['cashdrawer'] = {'command': '1b70001afa'}
    config['invoice_printer'] = {
        'autoprint': 'true',
        'name': 'FACTURE',
        'download_folder': 'C:/Users/Public/Downloads',
        'scan_frequency': '5',
        'purge_on_start': 'true',
        'file_extensions': '.pdf'
    }
    config['server'] = {'port': '22548', 'host': '0.0.0.0'}
    config['logs'] = {'folder': 'logs', 'filename': 'cashdrawer.log', 'retention_days': '30'}

# Configuration du logging
log_folder = config.get('logs', 'folder', fallback='logs')
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

# Configuration du logger avec rotation
log_filename = config.get('logs', 'filename', fallback='cashdrawer.log')
log_file = os.path.join(log_folder, log_filename)
retention_days = int(config.get('logs', 'retention_days', fallback='30'))
handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",
    interval=1,
    backupCount=retention_days
)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('cashdrawer')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = Flask(__name__)

def is_local_request():
    """Vérifie si la requête vient de localhost"""
    return request.remote_addr in ['127.0.0.1', 'localhost']

# Commande ESC/POS pour ouvrir le tiroir-caisse depuis la configuration
drawer_cmd_hex = config.get('cashdrawer', 'command', fallback='1b70001afa')
try:
    OPEN_DRAWER_CMD = binascii.unhexlify(drawer_cmd_hex)
except Exception as e:
    logger.error(f"Erreur lors de la conversion de la commande du tiroir-caisse: {str(e)}")
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
            logger.error("Ce service n'est compatible qu'avec Windows")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'ouverture du tiroir: {str(e)}")
        return False

@app.route('/open-cash-drawer', methods=['GET'])
def open_drawer():
    # Vérification que la requête vient de localhost
    if not is_local_request():
        logger.warning(f"Tentative d'accès distant à l'ouverture du tiroir depuis {request.remote_addr}")
        return jsonify({"status": "error", "message": "Accès refusé - Local uniquement"}), 403

    try:
        success = open_cashdrawer()
        if success:
            logger.info("Tiroir-caisse ouvert avec succès")
            return jsonify({"status": "success", "message": "Tiroir-caisse ouvert"}), 200
        else:
            return jsonify({"status": "error", "message": "Erreur lors de l'ouverture du tiroir"}), 500
    except Exception as e:
        logger.error(f"Erreur serveur: {str(e)}")
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
        logger.info(f"Téléchargement des logs depuis {request.remote_addr}")
        return send_file(log_file, as_attachment=True, download_name='cashdrawer.log')
    except Exception as e:
        logger.error(f"Erreur lors de l'accès aux logs: {str(e)}")
        return jsonify({"status": "error", "message": "Impossible d'accéder aux logs"}), 500

# Fonction pour imprimer un fichier PDF
def print_pdf_file(file_path, printer_name):
    try:
        if platform.system() == 'Windows':
            win32api.ShellExecute(
                0,
                "print",
                file_path,
                f'/d:"{printer_name}"',
                ".",
                0
            )
            logger.info(f"Fichier {file_path} envoyé à l'imprimante {printer_name}")
            return True
        else:
            logger.error("L'impression de PDF n'est compatible qu'avec Windows")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'impression du fichier {file_path}: {str(e)}")
        return False

# Fonction pour purger un dossier
def purge_folder(folder_path, extensions):
    try:
        count = 0
        for ext in extensions:
            files = glob.glob(os.path.join(folder_path, f"*{ext}"))
            for file in files:
                os.remove(file)
                count += 1
        logger.info(f"Purge du dossier {folder_path}: {count} fichiers supprimés")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la purge du dossier {folder_path}: {str(e)}")
        return False

# Fonction pour scanner le dossier de téléchargement et imprimer les PDF
def scan_and_print_pdfs():
    # Récupération des paramètres de configuration
    printer_name = config.get('invoice_printer', 'name', fallback='FACTURE')
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
    scan_frequency = int(config.get('invoice_printer', 'scan_frequency', fallback='5'))
    purge_on_start = config.getboolean('invoice_printer', 'purge_on_start', fallback=True)
    file_extensions_str = config.get('invoice_printer', 'file_extensions', fallback='.pdf')
    file_extensions = [ext.strip() for ext in file_extensions_str.split(',')]
    
    # Vérification que le dossier existe
    if not os.path.exists(download_folder):
        try:
            os.makedirs(download_folder)
            logger.info(f"Dossier {download_folder} créé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier {download_folder}: {str(e)}")
            return
    
    # Purge du dossier au premier lancement si configuré
    if purge_on_start:
        purge_folder(download_folder, file_extensions)
    
    logger.info(f"Démarrage du scanner d'impression pour {printer_name} dans {download_folder}")
    
    # Boucle principale de scan
    while True:
        try:
            for ext in file_extensions:
                files = glob.glob(os.path.join(download_folder, f"*{ext}"))
                for file in files:
                    # Impression du fichier
                    success = print_pdf_file(file, printer_name)
                    
                    # Suppression du fichier après impression
                    if success:
                        try:
                            os.remove(file)
                            logger.info(f"Fichier {file} supprimé après impression")
                        except Exception as e:
                            logger.error(f"Erreur lors de la suppression du fichier {file}: {str(e)}")
            
            # Attente avant le prochain scan
            time.sleep(scan_frequency)
        except Exception as e:
            logger.error(f"Erreur lors du scan du dossier {download_folder}: {str(e)}")
            time.sleep(scan_frequency)

@app.route('/invoice-printer/status', methods=['GET'])
def invoice_printer_status():
    """Endpoint pour vérifier le statut de l'imprimante facture"""
    autoprint_enabled = config.getboolean('invoice_printer', 'autoprint', fallback=True)
    printer_name = config.get('invoice_printer', 'name', fallback='FACTURE')
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
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

@app.route('/invoice-printer/purge', methods=['GET'])
def invoice_printer_purge():
    """Endpoint pour purger le dossier de téléchargement"""
    # Vérification que la requête vient de localhost
    if not is_local_request():
        logger.warning(f"Tentative d'accès distant à la purge du dossier depuis {request.remote_addr}")
        return jsonify({"status": "error", "message": "Accès refusé - Local uniquement"}), 403
    
    download_folder = config.get('invoice_printer', 'download_folder', fallback='C:/Users/Public/Downloads')
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
    logger.info("Démarrage du service tiroir-caisse")
    try:
        # Vérification si l'impression automatique est activée
        autoprint_enabled = config.getboolean('invoice_printer', 'autoprint', fallback=True)
        
        if autoprint_enabled:
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
        
        app.run(
            host=host, 
            port=port,
            ssl_context=None  # Permet les requêtes HTTP et HTTPS
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du service: {str(e)}")

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
        'download_folder': 'C:\\Users\\Public\\Downloads',
        'scan_frequency': '5',
        'purge_on_start': 'true',
        'file_extensions': '.pdf'
    }
    config['server'] = {'port': '22548', 'host': '0.0.0.0'}
    config['logs'] = {'folder': 'logs', 'filename': 'cashdrawer.log', 'retention_days': '30'}

# Configuration du logging
log_folder = config.get('logs', 'folder', fallback='logs')
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

app = Flask(__name__)

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

# Fonction pour imprimer un fichier PDF
def print_pdf_file(file_path, printer_name):
    try:
        logger.info(f"Tentative d'impression du fichier: {file_path} sur l'imprimante: {printer_name}")
        
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
            # Essayer plusieurs méthodes d'impression
            try:
                # Méthode 1: Utiliser win32print directement
                logger.info(f"Tentative d'impression avec win32print (méthode 1)")
                
                try:
                    # Ouvrir l'imprimante
                    printer_handle = win32print.OpenPrinter(printer_name)
                    
                    try:
                        # Créer un job d'impression
                        job = win32print.StartDocPrinter(printer_handle, 1, (os.path.basename(file_path), None, "RAW"))
                        
                        try:
                            # Lire le fichier PDF
                            with open(file_path, 'rb') as f:
                                data = f.read()
                            
                            # Démarrer une page
                            win32print.StartPagePrinter(printer_handle)
                            
                            # Envoyer les données à l'imprimante
                            win32print.WritePrinter(printer_handle, data)
                            
                            # Terminer la page
                            win32print.EndPagePrinter(printer_handle)
                            
                            logger.info(f"Fichier {file_path} envoyé à l'imprimante {printer_name} avec win32print")
                            return True
                        finally:
                            # Terminer le job d'impression
                            win32print.EndDocPrinter(printer_handle)
                    finally:
                        # Fermer l'imprimante
                        win32print.ClosePrinter(printer_handle)
                except Exception as e:
                    logger.warning(f"Échec de la méthode 1 (win32print): {str(e)}")
                    
                # Méthode 2: Utiliser ShellExecute
                logger.info(f"Tentative d'impression avec win32api.ShellExecute (méthode 2)")
                try:
                    win32api.ShellExecute(
                        0,
                        "print",
                        file_path,
                        f'/d:"{printer_name}"',
                        ".",
                        0
                    )
                    logger.info(f"Fichier {file_path} envoyé à l'imprimante {printer_name} avec ShellExecute")
                    return True
                except Exception as e:
                    logger.warning(f"Échec de la méthode 2 (ShellExecute): {str(e)}")
                
                # Méthode 3: Utiliser une commande système
                logger.info(f"Tentative d'impression avec commande système (méthode 3)")
                try:
                    import subprocess
                    # Utiliser la commande système pour imprimer
                    cmd = f'print /d:"{printer_name}" "{file_path}"'
                    logger.info(f"Exécution de la commande: {cmd}")
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"Fichier {file_path} envoyé à l'imprimante {printer_name} avec commande système")
                        return True
                    else:
                        logger.warning(f"Échec de la méthode 3 (commande système): {result.stderr}")
                except Exception as e:
                    logger.warning(f"Échec de la méthode 3 (commande système): {str(e)}")
                
                # Si toutes les méthodes ont échoué
                log_error_once(f"Toutes les méthodes d'impression ont échoué pour le fichier {file_path}", f"all_print_methods_failed_{file_path}")
                return False
                
            except Exception as e:
                log_error_once(f"Erreur générale lors de l'impression: {str(e)}", "general_print_error")
                return False
        else:
            log_error_once(f"Ce service n'est compatible qu'avec Windows. Système détecté: {platform.system()}", "print_os_not_windows")
            return False
    except Exception as e:
        log_error_once(f"Erreur lors de l'impression du fichier {file_path}: {str(e)}", f"print_file_error_{file_path}")
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
                        
                        # Impression du fichier
                        success = print_pdf_file(file, printer_name)
                        
                        if success:
                            print_success_count += 1
                            logger.info(f"Impression réussie: {file} (Total réussi: {print_success_count})")
                            
                            # Suppression du fichier après impression
                            try:
                                os.remove(file)
                                delete_success_count += 1
                                logger.info(f"Fichier {file} supprimé après impression (Total supprimé: {delete_success_count})")
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
    print("Démarrage du service tiroir-caisse")
    logger.info("Démarrage du service tiroir-caisse")
    
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

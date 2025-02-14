from flask import Flask, jsonify, send_file, request
from escpos.printer import Win32
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os
import platform

# Configuration du logging
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configuration du logger avec rotation
log_file = os.path.join('logs', 'cashdrawer.log')
handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",
    interval=1,
    backupCount=30  # Garde les logs pendant 30 jours
)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('cashdrawer')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = Flask(__name__)

def is_local_request():
    """Vérifie si la requête vient de localhost"""
    return request.remote_addr in ['127.0.0.1', 'localhost']

def open_cashdrawer():
    try:
        if platform.system() == 'Windows':
            # Utilise l'imprimante nommée "TICKET" sous Windows
            printer = Win32('TICKET')
        else:
            logger.error("Ce service n'est compatible qu'avec Windows")
            return False
            
        printer.cashdraw(2)  # Ouvre le tiroir-caisse
        printer.close()
        return True
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
        "remote_addr": request.remote_addr
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

if __name__ == '__main__':
    logger.info("Démarrage du service tiroir-caisse")
    # Écoute sur toutes les interfaces pour permettre l'accès distant aux logs
    app.run(host='0.0.0.0', port=22548)

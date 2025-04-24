#!/usr/bin/env python3
"""
Script de test pour l'impression directe via socket
"""
import os
import sys
import logging

# Configuration du logging basique pour voir les messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_impression')

# Dictionnaire pour suivre les erreurs déjà enregistrées (simplifié par rapport à app.py)
error_cache = {}
def log_error_once(message, error_type="general"):
    """Enregistre une erreur une seule fois jusqu'à ce qu'elle soit résolue"""
    error_key = f"{error_type}:{message}"
    if error_key not in error_cache:
        logger.error(message)
        error_cache[error_key] = True
        return True
    return False

# Fonction d'impression simplifiée basée sur la nouvelle implémentation dans app.py
def print_pdf_file(file_path, printer_name):
    try:
        logger.info(f"Tentative d'impression du fichier: {file_path} sur l'imprimante {printer_name} via socket")
        
        # Vérification que le fichier existe
        if not os.path.exists(file_path):
            log_error_once(f"Fichier introuvable: {file_path}", f"file_not_found_{file_path}")
            return False
            
        # Vérification des permissions
        if not os.access(file_path, os.R_OK):
            log_error_once(f"Permissions insuffisantes pour lire le fichier: {file_path}", f"file_permission_{file_path}")
            return False
        
        # Récupérer l'adresse IP et le port de l'imprimante à partir du nom
        # Par défaut, on utilise l'adresse 172.17.240.20 et le port 9100
        printer_ip = "172.17.240.20"
        printer_port = 9100
        
        # Si le nom de l'imprimante contient l'adresse IP et le port au format "nom@ip:port"
        if "@" in printer_name:
            try:
                name_part, ip_part = printer_name.split("@", 1)
                if ":" in ip_part:
                    ip, port = ip_part.split(":", 1)
                    printer_ip = ip
                    printer_port = int(port)
                else:
                    printer_ip = ip_part
            except Exception as e:
                logger.warning(f"Format d'adresse d'imprimante invalide: {printer_name}. Utilisation des valeurs par défaut. Erreur: {str(e)}")
        
        logger.info(f"Impression vers l'imprimante à l'adresse {printer_ip}:{printer_port}")
        
        # Impression directe via socket
        try:
            # Ouvrir le fichier en mode binaire
            with open(file_path, 'rb') as f:
                contenu = f.read()
            
            # Établir une connexion avec l'imprimante
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)  # Timeout de 10 secondes
            s.connect((printer_ip, printer_port))
            
            # Envoyer le contenu du fichier
            s.sendall(contenu)
            
            # Fermer la connexion
            s.close()
            
            logger.info(f"Fichier {file_path} envoyé avec succès à l'imprimante {printer_ip}:{printer_port}")
            return True
        except socket.error as e:
            log_error_once(f"Erreur de connexion à l'imprimante {printer_ip}:{printer_port}: {str(e)}", f"socket_error_{printer_ip}:{printer_port}")
            return False
        except Exception as e:
            log_error_once(f"Erreur lors de l'impression via socket: {str(e)}", f"socket_general_error_{file_path}")
            return False
    except Exception as e:
        log_error_once(f"Erreur lors de l'impression du fichier {file_path}: {str(e)}", f"print_file_error_{file_path}")
        return False

if __name__ == "__main__":
    # Fichier à imprimer
    pdf_file = "test.pdf"
    
    # Nom de l'imprimante (peut être au format "nom@ip:port")
    printer_name = "FACTURE@172.17.240.20:9100"
    
    # Test d'impression
    print("=== TEST D'IMPRESSION DIRECTE VIA SOCKET ===")
    print(f"Fichier: {pdf_file}")
    print(f"Imprimante: {printer_name}")
    print("==========================================")
    
    success = print_pdf_file(pdf_file, printer_name)
    
    if success:
        print("\n✅ IMPRESSION RÉUSSIE!")
    else:
        print("\n❌ ÉCHEC DE L'IMPRESSION!")

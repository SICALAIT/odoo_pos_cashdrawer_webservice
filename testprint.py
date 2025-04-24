#!/usr/bin/env python3
"""
Script simple pour imprimer un fichier PDF vers une imprimante réseau.
"""
import socket

def imprimer_fichier(fichier_path, imprimante_ip, imprimante_port):
    """
    Envoie un fichier directement à une imprimante réseau via socket.
    
    Args:
        fichier_path (str): Chemin vers le fichier à imprimer
        imprimante_ip (str): Adresse IP de l'imprimante
        imprimante_port (int): Port de l'imprimante (généralement 9100 pour RAW)
    """
    try:
        # Ouvrir le fichier en mode binaire
        with open(fichier_path, 'rb') as f:
            contenu = f.read()
        
        # Établir une connexion avec l'imprimante
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((imprimante_ip, imprimante_port))
        
        # Envoyer le contenu du fichier
        s.sendall(contenu)
        
        # Fermer la connexion
        s.close()
        
        print(f"Le fichier {fichier_path} a été envoyé à l'imprimante {imprimante_ip}:{imprimante_port}")
        return True
    
    except FileNotFoundError:
        print(f"Erreur: Le fichier {fichier_path} n'a pas été trouvé.")
        return False
    except socket.error as e:
        print(f"Erreur de connexion à l'imprimante: {e}")
        return False
    except Exception as e:
        print(f"Une erreur s'est produite: {e}")
        return False

if __name__ == "__main__":
    # Configuration
    fichier_pdf = "test.pdf"
    imprimante_ip = "172.17.240.20"
    imprimante_port = 9100
    
    # Imprimer le fichier
    imprimer_fichier(fichier_pdf, imprimante_ip, imprimante_port)

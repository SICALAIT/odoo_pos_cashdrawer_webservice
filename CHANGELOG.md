# Changelog

Tous les changements notables apportés à ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-04-22

### Ajouté
- Section d'authentification [auth] dans le fichier config.ini par défaut
- Champs vides pour password_hash et salt dans la section [auth]
- Création du fichier CHANGELOG.md pour suivre les modifications du projet
- Fonctionnalité de purge des logs depuis l'interface web

### Modifié
- Mise à jour du processus de génération du fichier config.ini dans app.py et build.py pour inclure la section [auth]
- Mise à jour du README.md pour refléter la nouvelle structure du fichier config.ini

### Corrigé
- Génération correcte des champs d'authentification lors de la première ouverture du webservice

# NovaMath v1.87

Version autonome de NovaMath — ce dossier contient tout ce qu'il faut pour la
lancer, y compris les banques d'exercices et les modèles IA. Il peut être
copié ou déplacé sur un autre PC sans configuration supplémentaire (Python
doit simplement être installé).

## Lancer le site

- **Windows (double-clic)** : `RUN.bat`
- **PowerShell** : clic droit sur `RUN.ps1` → *Exécuter avec PowerShell*
  (ou dans un terminal : `powershell -ExecutionPolicy Bypass -File .\RUN.ps1`)

Le script :
1. vérifie que le backend et le frontend sont bien présents dans ce dossier ;
2. détecte Python (environnement virtuel `.venv/` s'il existe, sinon Python système) ;
3. installe automatiquement les dépendances manquantes (`requirements.txt`) ;
4. démarre le serveur NovaMath v1.87 (la base de données SQLite est
   initialisée automatiquement à ce moment-là si elle n'existe pas encore) ;
5. attend qu'il soit prêt, puis ouvre automatiquement le navigateur sur
   `http://127.0.0.1:5050/`.

## Arrêter le serveur

Ferme la fenêtre de console du serveur (titrée « NovaMath v1.87 - Serveur »
sous RUN.bat, ou la fenêtre du processus Python sous RUN.ps1), ou tape Ctrl+C
dans cette fenêtre.

## Résolution des erreurs courantes

- **« Python n'est pas installé »** : installe Python depuis
  https://www.python.org/downloads/ (coche « Add Python to PATH » pendant
  l'installation), puis relance RUN.bat.
- **« Le port 5050 est déjà utilisé »** : une autre instance de NovaMath
  (ou un autre programme) écoute déjà sur ce port. Ferme-la, ou modifie la
  valeur du port en haut de RUN.bat / RUN.ps1.
- **« webapp\server.py introuvable »** : le dossier de version est incomplet
  (fichiers manquants) — reprends une copie complète du dossier.
- **Le navigateur ne s'ouvre pas** : ouvre-le manuellement à l'adresse
  `http://127.0.0.1:5050/` une fois la fenêtre du serveur affichée.

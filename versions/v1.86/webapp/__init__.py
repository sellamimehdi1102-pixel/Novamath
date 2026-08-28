"""
Rend `webapp/` important en tant que package (nécessaire pour
`gunicorn webapp.server:app` lancé depuis la racine du projet).

webapp/server.py et les modules qu'il importe (auth, config, billing_service,
etc.) utilisent des imports absolus "plats" (`import auth`, pas
`from . import auth`), en cohérence avec `python webapp/server.py` qui place
`webapp/` en tête de sys.path. On reproduit ce même effet ici pour que ces
imports continuent de fonctionner quand le package est chargé par Gunicorn
depuis un autre répertoire de travail.
"""
import os
import sys

_WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))
if _WEBAPP_DIR not in sys.path:
    sys.path.insert(0, _WEBAPP_DIR)

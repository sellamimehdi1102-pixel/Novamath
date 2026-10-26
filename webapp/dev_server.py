"""Serveur de DÉVELOPPEMENT local de Mathadap — une seule instance, une seule
adresse (http://127.0.0.1:5050). Jamais utilisé en production : gunicorn
importe `server.app` directement et n'exécute jamais ce module.

Utilisé par `python webapp/server.py` et par tools/preview_isolated_server.py
(lui-même lancé par tools/run_preview.py, la commande officielle).

Pourquoi (constaté le 2026-10-25) : Werkzeug lie son socket avec
SO_REUSEADDR (`allow_reuse_address = True`). Sous Windows, cette option
permet à un SECOND processus de se lier au même port, sans erreur, tant que
le premier l'a aussi utilisée : deux serveurs Mathadap écoutaient ainsi
ensemble 127.0.0.1:5050, et le navigateur tombait sur l'un ou l'autre.
Mesuré sur ce poste : seule la combinaison SO_REUSEADDR + SO_REUSEADDR
donne deux écoutes ; SO_EXCLUSIVEADDRUSE fait échouer toute autre liaison
(quelles que soient ses options), et se relie immédiatement après un arrêt.

Ce module :
- réserve le port en EXCLUSIVITÉ (Windows : SO_EXCLUSIVEADDRUSE ; ailleurs,
  SO_REUSEADDR n'autorise déjà pas deux écoutes) — la liaison elle-même est
  le test, sans fenêtre de concurrence entre « vérifier » et « lancer » ;
- garde le rechargeur Werkzeug en mode debug : le processus parent détient
  le socket pendant toute la session et chaque redémarrage du processus
  enfant (modification Python, contenu de cours ou banque reconstruit)
  réutilise CE socket, donc le même port ;
- rattache le serveur et ses enfants à un « Job Object » Windows fermé à la
  mort du parent : aucun enfant du rechargeur ne survit à son parent ;
- inscrit l'instance dans un fichier d'état (PID, date de création, mode)
  pour que tools/run_preview.py la reconnaisse avec certitude.
"""
import atexit
import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 5050
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Contenus chargés une fois en mémoire par server.py (_class_bank_cache...) :
# leur reconstruction (tools/build_*.py) redémarre le serveur, comme un .py.
CONTENT_GLOBS = (
    (PROJECT_ROOT, "exercises_*.json"),
    (PROJECT_ROOT / "webapp" / "course_content", "**/*.json"),
)


def state_path(port: int) -> Path:
    return Path(tempfile.gettempdir()) / f"mathadap-dev-{port}.json"


def read_state(port: int):
    """État de l'instance inscrite pour `port`, ou None (absent, illisible ou
    processus disparu / remplacé — PID réutilisé : date de création comparée)."""
    try:
        state = json.loads(state_path(port).read_text(encoding="utf-8"))
        import psutil

        proc = psutil.Process(int(state["pid"]))
        if abs(proc.create_time() - float(state["create_time"])) > 1:
            return None
        return state
    except Exception:
        return None


def exclusive_socket(port: int, host: str = HOST) -> socket.socket:
    """Socket lié en exclusivité à host:port (OSError si le port est pris)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
    except OSError:
        sock.close()
        raise
    return sock


def _patch_werkzeug_bind():
    """La liaison de Werkzeug passe en exclusivité sous Windows (voir en-tête)."""
    if os.name != "nt":
        return
    from werkzeug.serving import BaseWSGIServer

    if getattr(BaseWSGIServer, "_mathadap_exclusive", False):
        return

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    BaseWSGIServer.allow_reuse_address = False
    BaseWSGIServer.server_bind = server_bind
    BaseWSGIServer._mathadap_exclusive = True


_JOB_HANDLE = None


def kill_children_with_this_process():
    """Windows : place ce processus (et tous ceux qu'il lancera) dans un Job
    Object fermé à sa mort (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) — même tué
    brutalement, il n'abandonne aucun serveur enfant à l'écoute. Sans effet
    ailleurs ou si Windows refuse (le nettoyage par psutil reste en place)."""
    global _JOB_HANDLE
    if os.name != "nt" or _JOB_HANDLE is not None:
        return _JOB_HANDLE is not None
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount",
                                                         "OtherOperationCount", "ReadTransferCount",
                                                         "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return False
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) and \
        kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess())
    if not ok:
        kernel32.CloseHandle(job)
        return False
    _JOB_HANDLE = job  # handle conservé jusqu'à la fin du processus
    return True


def listeners(port: int):
    """[(pid, adresse)] des processus qui écoutent `port` (toutes adresses)."""
    try:
        import psutil

        return sorted({(c.pid, c.laddr.ip) for c in psutil.net_connections(kind="tcp")
                       if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port})
    except Exception:
        return []


def process_label(pid):
    try:
        import psutil

        proc = psutil.Process(pid)
        started = time.strftime("%d/%m/%Y %H:%M", time.localtime(proc.create_time()))
        return f"PID {pid} ({proc.name()}, lancé le {started}) : {' '.join(proc.cmdline())}"
    except Exception:
        return f"PID {pid}"


def describe_mode(state) -> str:
    preview = state.get("preview") or "aucune"
    return (f"données {state.get('data', '?')}, classes en prévisualisation : {preview}, "
            f"Stripe {'actif' if state.get('stripe') else 'désactivé'}")


def _content_files():
    files = []
    for root, pattern in CONTENT_GLOBS:
        if root.is_dir():
            files.extend(str(p) for p in root.glob(pattern) if p.is_file())
    return files


def run(app, *, debug: bool, data: str = "réelles (data/)"):
    """Lance `app` sur 127.0.0.1:$PORT (5050 par défaut), seul sur ce port."""
    from werkzeug.serving import is_running_from_reloader

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    _patch_werkzeug_bind()
    if not is_running_from_reloader():
        kill_children_with_this_process()
        try:
            exclusive_socket(port).close()
        except OSError:
            print(f"\n✗ Le port {port} est déjà utilisé : Mathadap ne démarre PAS (et ne prend jamais un autre port).",
                  file=sys.stderr, flush=True)
            for pid, ip in listeners(port):
                print(f"    {ip}:{port} — {process_label(pid)}", file=sys.stderr, flush=True)
            print("  Pour retrouver ou redémarrer Mathadap : python tools/run_preview.py "
                  "(il reconnaît une instance déjà lancée).", file=sys.stderr, flush=True)
            sys.exit(2)
        import psutil

        me = psutil.Process()
        state = {
            "pid": me.pid, "create_time": me.create_time(), "port": port, "url": f"http://{HOST}:{port}/",
            "data": data, "preview": os.environ.get("NOVAMATH_PREVIEW_CURRICULA", "").strip(),
            "stripe": bool(os.environ.get("STRIPE_SECRET_KEY", "").strip()),
            "launcher": os.environ.get("MATHADAP_LAUNCHER", "direct"), "started": time.time(),
            "reloader": bool(debug),
        }
        path = state_path(port)
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

        def _forget():
            current = read_state(port)
            if current and current["pid"] == me.pid:
                path.unlink(missing_ok=True)

        atexit.register(_forget)
    app.run(host=HOST, port=port, debug=debug, use_reloader=debug, threaded=True,
            extra_files=_content_files() if debug else None)

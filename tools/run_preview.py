"""Commande OFFICIELLE pour consulter Mathadap en local — une seule instance,
une seule adresse : http://127.0.0.1:5050 (site complet, Quatrième en
prévisualisation).

    python tools/run_preview.py                  # tes données habituelles (data/)
    python tools/run_preview.py --donnees-test   # base et fichiers utilisateur isolés
    python tools/run_preview.py --statut         # quelle instance tourne, dans quel mode
    python tools/run_preview.py --redemarrer     # redémarrage contrôlé (même adresse)
    python tools/run_preview.py --arreter        # arrête l'instance lancée par ce lanceur
    (npm run dev = la première commande ; npm run dev:donnees-test = la deuxième)

Options : --no-browser, --no-build, --sans-surveillance (pas de recompilation
automatique du frontend), --stripe (garder Stripe, voir plus bas), liste
d'ids en argument (défaut : quatrieme). `--port` est réservé aux suites de
tests automatisées : le lanceur ne choisit JAMAIS un autre port de lui-même.

Une seule instance (voir webapp/dev_server.py) : le serveur réserve le port
en exclusivité (sous Windows, Werkzeug laissait sinon deux serveurs écouter
ensemble 127.0.0.1:5050) et s'inscrit dans un fichier d'état. Au lancement :
- port libre : Mathadap démarre sur 5050 ;
- Mathadap déjà lancé dans le mode demandé : rien n'est démarré, l'adresse
  est rappelée ;
- Mathadap lancé dans un AUTRE mode : explication, puis `--redemarrer` ;
- ancien serveur Mathadap non inscrit (lancé avant ce lanceur) : il n'est
  jamais arrêté automatiquement — son PID et la commande pour l'arrêter
  sont affichés ;
- autre application sur le port : échec explicite, aucun autre port.
Seule une instance inscrite (PID et date de création vérifiés) peut être
arrêtée par `--redemarrer` / `--arreter`.

Modifications visibles sur la même adresse :
- frontend (webapp/static/) : `vite build --watch` recompile static-dist/
  (servi par Flask) en quelques secondes ; recharger la page ;
- Python, cours ou banques d'exercices reconstruits : le rechargeur Werkzeug
  redémarre le serveur tout seul, sur le même socket donc le même port ;
- tout le reste (variables d'environnement, `.env`, nouvelle dépendance) :
  `python tools/run_preview.py --redemarrer`.

Équivaut à définir NOVAMATH_PREVIEW_CURRICULA avant de lancer
`python webapp/server.py` : aucun fichier de configuration modifié (ni
`.env`, ni `published` dans curriculum_registry.py). Les protections restent
celles du registre : le serveur refuse de démarrer si FLASK_ENV vaut
"production", ou si un id est inconnu ou déjà publié — voir
curriculum_registry.validate_registry(). Le serveur n'écoute que 127.0.0.1.

Paiements : Stripe est DÉSACTIVÉ par défaut (STRIPE_SECRET_KEY vide pour ce
seul processus — `.env` n'est jamais modifié, et load_dotenv n'écrase pas une
variable déjà définie). La clé de `.env` peut être une clé live : un clic de
test sur « Passer à Premium/Ultra » créerait sinon un vrai client et une
vraie session de paiement. Pour tester les plans, utiliser le mode test
Owner (NOVAMATH_OWNER_USER_ID, voir owner_test_plan_service.py). `--stripe`
conserve la configuration de `.env`.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "webapp"))
import dev_server  # noqa: E402

SERVER = PROJECT_ROOT / "webapp" / "server.py"
STATIC_DIR = PROJECT_ROOT / "webapp" / "static"
STATIC_DIST_DIR = PROJECT_ROOT / "webapp" / "static-dist"
ISOLATED_SERVER = PROJECT_ROOT / "tools" / "preview_isolated_server.py"
# Hors du dépôt (aucun fichier non suivi par git) et conservé d'un lancement à l'autre.
DEFAULT_SANDBOX_DIR = Path(tempfile.gettempdir()) / "mathadap-preview"
HOST = dev_server.HOST
STARTUP_TIMEOUT_S = 120
REAL_DATA = "réelles (data/)"


def _newest_mtime(root, skip_dirs=()):
    newest = 0.0
    for path in root.rglob("*"):
        if path.is_file() and not any(part in skip_dirs for part in path.relative_to(root).parts):
            newest = max(newest, path.stat().st_mtime)
    return newest


def static_dist_is_stale():
    """True si static-dist/ existe et qu'une source frontend (hors tests) est
    plus récente que la dernière compilation."""
    if not STATIC_DIST_DIR.is_dir():
        return False  # Flask sert alors webapp/static/ directement : toujours à jour.
    return _newest_mtime(STATIC_DIR, skip_dirs=("__tests__",)) > _newest_mtime(STATIC_DIST_DIR)


def served_curricula(port, host=HOST, timeout=2.0):
    """Liste renvoyée par /api/curricula sur host:port, ou None si aucune
    réponse exploitable (donc pas un serveur Mathadap)."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/curricula", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, list) and all(isinstance(c, dict) and "classLevel" in c for c in data):
        return data
    return None


def port_is_free(port):
    try:
        dev_server.exclusive_socket(port).close()
        return True
    except OSError:
        return False


def inspect_port(port):
    """("libre" | "inscrit" | "ancien" | "autre", état inscrit, écouteurs)."""
    found = dev_server.listeners(port)
    if not found and port_is_free(port):
        return "libre", None, []
    state = dev_server.read_state(port)
    if state and any(pid == state["pid"] for pid, _ in found):
        return "inscrit", state, found
    if found and served_curricula(port) is not None:
        return "ancien", None, found
    return "autre", None, found


def same_mode(state, wanted):
    return all(state.get(k) == v for k, v in wanted.items())


def stop_instance(state, port, timeout=20):
    """Arrête une instance INSCRITE (processus et tous ses enfants), puis
    attend que le port soit libéré."""
    import psutil

    try:
        root = psutil.Process(int(state["pid"]))
        procs = root.children(recursive=True) + [root]
    except psutil.Error:
        procs = []
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(procs, timeout=5)
    for proc in alive:
        try:
            proc.kill()
        except psutil.Error:
            pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not dev_server.listeners(port) and port_is_free(port):
            dev_server.state_path(port).unlink(missing_ok=True)
            return True
        time.sleep(0.5)
    return False


def own_tree_pids(process):
    try:
        import psutil

        return {process.pid} | {c.pid for c in psutil.Process(process.pid).children(recursive=True)}
    except Exception:
        return {process.pid}


def wait_until_served(port, process, timeout=STARTUP_TIMEOUT_S):
    """Attend que NOTRE serveur réponde sur `port` : /api/curricula, et
    écouteur appartenant au processus lancé (jamais un autre serveur)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return None
        curricula = served_curricula(port)
        if curricula is not None and {pid for pid, _ in dev_server.listeners(port)} & own_tree_pids(process):
            return curricula
        time.sleep(1)
    return None


def stop_tree(process):
    """Arrête un processus lancé par ce lanceur ET ses enfants (le rechargeur
    Werkzeug relance le serveur dans un processus enfant)."""
    if process is None or process.poll() is not None:
        return
    try:
        import psutil

        children = psutil.Process(process.pid).children(recursive=True)
    except Exception:
        children = []
    for child in children:
        try:
            child.kill()
        except Exception:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def start_frontend_watch():
    """`vite build --watch` : recompile static-dist/ à chaque modification de
    webapp/static/. --emptyOutDir=false : en surveillance, Vite viderait sinon
    le dossier à CHAQUE recompilation (pages absentes quelques secondes).
    Seules les lignes utiles de Vite sont relayées."""
    npx = shutil.which("npx")
    if npx is None:
        print("  (npx introuvable : pas de recompilation automatique du frontend — lancer `npm run build`)", flush=True)
        return None
    process = subprocess.Popen(
        [npx, "vite", "build", "--watch", "--emptyOutDir=false"], cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )

    def relay():
        for line in process.stdout:
            text = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()  # sans les codes couleur de Vite
            if "built in" in text:
                print(f"[frontend] recompilé ({text.split('built in')[-1].strip()}) — recharge la page.", flush=True)
            elif "error" in text.lower():
                print(f"[frontend] {text}", flush=True)

    threading.Thread(target=relay, daemon=True).start()
    return process


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("curricula", nargs="?", default="quatrieme", help="ids séparés par des virgules (défaut : quatrieme)")
    parser.add_argument("--port", type=int, default=dev_server.DEFAULT_PORT,
                        help="réservé aux suites de tests automatisées (défaut et usage normal : 5050)")
    parser.add_argument("--no-build", action="store_true", help="ne pas recompiler un frontend périmé au démarrage")
    parser.add_argument("--sans-surveillance", action="store_true", help="ne pas recompiler le frontend à chaque modification")
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    parser.add_argument("--stripe", action="store_true", help="garder Stripe actif (désactivé par défaut)")
    parser.add_argument(
        "--donnees-test", nargs="?", const=str(DEFAULT_SANDBOX_DIR), default=None, metavar="DOSSIER",
        help=f"base et fichiers utilisateur isolés (défaut : {DEFAULT_SANDBOX_DIR}) — tes comptes réels ne sont pas touchés",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--statut", action="store_true", help="afficher l'instance en cours et quitter")
    actions.add_argument("--redemarrer", action="store_true", help="arrêter l'instance inscrite puis relancer")
    actions.add_argument("--arreter", action="store_true", help="arrêter l'instance inscrite et quitter")
    args = parser.parse_args(argv)
    port = args.port
    url_root = f"http://{HOST}:{port}"
    expected_ids = [c.strip() for c in args.curricula.split(",") if c.strip()]
    data_dir = str(Path(args.donnees_test).resolve()) if args.donnees_test else None
    wanted = {"preview": args.curricula, "data": f"de test ({data_dir})" if data_dir else REAL_DATA,
              "stripe": bool(args.stripe)}
    dev_server.kill_children_with_this_process()

    kind, state, found = inspect_port(port)
    if args.statut:
        if kind == "libre":
            print(f"Aucun Mathadap ne tourne sur {url_root}.")
        elif kind == "inscrit":
            print(f"Mathadap tourne sur {url_root}/ — PID {state['pid']}, {dev_server.describe_mode(state)}.")
        else:
            print(f"Port {port} occupé ({'ancien serveur Mathadap non inscrit' if kind == 'ancien' else 'autre application'}) :")
            for pid, ip in found:
                print(f"    {ip}:{port} — {dev_server.process_label(pid)}")
        return 0
    if args.arreter:
        if kind != "inscrit":
            print(f"Aucune instance inscrite à arrêter sur le port {port} (état : {kind}).")
            return 0 if kind == "libre" else 1
        ok = stop_instance(state, port)
        print("✓ Mathadap arrêté, port libéré." if ok else f"✗ Le port {port} n'a pas été libéré.")
        return 0 if ok else 1

    if kind == "inscrit":
        if not args.redemarrer and same_mode(state, wanted):
            print(f"\n✓ Mathadap fonctionne déjà : {url_root}/  ({dev_server.describe_mode(state)})", flush=True)
            print("  Aucun second serveur n'est démarré. Redémarrage contrôlé : "
                  "python tools/run_preview.py --redemarrer", flush=True)
            if not args.no_browser:
                webbrowser.open(f"{url_root}/choisir-classe.html")
            return 0
        if not args.redemarrer:
            print(f"\n⚠ Mathadap tourne déjà sur {url_root}/ dans un AUTRE mode :", flush=True)
            print(f"    en cours  : {dev_server.describe_mode(state)}", flush=True)
            print(f"    demandé   : {dev_server.describe_mode(wanted)}", flush=True)
            print("  Rien n'est démarré. Pour passer au mode demandé (même adresse), relance la même "
                  "commande avec --redemarrer.", flush=True)
            return 1
        print(f"Redémarrage contrôlé : arrêt de l'instance PID {state['pid']}…", flush=True)
        if not stop_instance(state, port):
            print(f"✗ Le port {port} n'a pas été libéré : serveur non démarré.", flush=True)
            return 1
    elif kind == "ancien":
        print(f"\n✗ Un ANCIEN serveur Mathadap occupe {url_root} — lancé hors de ce lanceur, il n'est "
              "pas arrêté automatiquement :", flush=True)
        for pid, ip in found:
            print(f"    {ip}:{port} — {dev_server.process_label(pid)}", flush=True)
        pids = sorted({pid for pid, _ in found})
        print("  Arrête-le (Ctrl+C dans sa fenêtre, ou dans PowerShell : "
              f"Stop-Process -Id {', '.join(map(str, pids))}), puis relance cette commande.", flush=True)
        return 1
    elif kind == "autre":
        print(f"\n✗ Le port {port} est occupé par une autre application : Mathadap ne démarre pas "
              "(et n'utilise jamais un autre port).", flush=True)
        for pid, ip in found:
            print(f"    {ip}:{port} — {dev_server.process_label(pid)}", flush=True)
        if not found:
            print("    (écouteur non identifiable : port réservé par Windows ou accès refusé)", flush=True)
        return 1

    if not args.no_build and static_dist_is_stale():
        npm = shutil.which("npm")
        if npm is None:
            print("Attention : webapp/static-dist/ est plus ancien que les sources et npm est introuvable — "
                  "l'interface affichée sera périmée (lancer `npm run build`).", flush=True)
        else:
            print("Frontend compilé périmé : npm run build…", flush=True)
            if subprocess.call([npm, "run", "build"], cwd=PROJECT_ROOT) != 0:
                print("Échec de `npm run build` : serveur non démarré.", flush=True)
                return 1

    env = dict(os.environ, NOVAMATH_PREVIEW_CURRICULA=args.curricula, PORT=str(port), MATHADAP_LAUNCHER="run_preview")
    if not args.stripe:
        env["STRIPE_SECRET_KEY"] = ""
        env["STRIPE_WEBHOOK_SECRET"] = ""
    print(f"\nDémarrage de Mathadap ({args.curricula} en prévisualisation) sur {url_root}…", flush=True)
    command = [sys.executable, str(ISOLATED_SERVER), data_dir] if data_dir else [sys.executable, str(SERVER)]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=env)
    watcher = None
    try:
        curricula = wait_until_served(port, process)
        if curricula is None:
            print("\n✗ Le serveur n'a pas démarré (voir les messages ci-dessus).", flush=True)
            return 1
        served = {c["classLevel"]: c for c in curricula}
        missing = [i for i in expected_ids if i not in served]
        if missing:
            print(f"\n✗ Le serveur ne sert pas : {', '.join(missing)}. Arrêt.", flush=True)
            return 1
        if not args.sans_surveillance:
            watcher = start_frontend_watch()
        print("\n" + "=" * 72, flush=True)
        print(f"✓ Mathadap prêt — {url_root}/  ({len(curricula)} classes servies)", flush=True)
        for c in curricula:
            tag = "  ← en prévisualisation" if c["classLevel"] in expected_ids else ""
            print(f"    {c['label']} : {c['totalExercises']} exercices, {c['chapters']} chapitre(s), "
                  f"{c['notions']} notions{tag}", flush=True)
        if data_dir:
            print(f"\n  Données de test isolées : {data_dir} (crée un compte d'essai ; tes comptes réels "
                  "ne sont pas utilisés).", flush=True)
        else:
            print("\n  Données : ta base habituelle (data/) — connecte-toi avec ton compte.", flush=True)
        if not args.stripe:
            print("  Stripe désactivé : aucun paiement possible (option --stripe pour le garder).", flush=True)
        print("  Modifications : frontend recompilé automatiquement (recharger la page) ; Python, cours et "
              "banques : redémarrage automatique du serveur ; .env : --redemarrer.", flush=True)
        print("  Arrêt : Ctrl+C dans cette fenêtre (ou python tools/run_preview.py --arreter).", flush=True)
        print("=" * 72 + "\n", flush=True)
        if not args.no_browser:
            webbrowser.open(f"{url_root}/choisir-classe.html")
        return process.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        stop_tree(watcher)
        stop_tree(process)


if __name__ == "__main__":
    sys.exit(main())

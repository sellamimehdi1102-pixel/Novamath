"""
Sauvegardes de la base de données NovaMath.

Architecture stricte, identique au reste des services :

    server.py  →  backup_service.py  →  db.py

jamais l'inverse. Compatible SQLite (mode réel de ce projet aujourd'hui, voir
db.py::DB_PATH) ET PostgreSQL (branché dès maintenant via DATABASE_URL, pour
un futur portage sans re-concevoir ce module — non exercé en pratique tant
qu'aucune connexion Postgres n'existe ailleurs dans le projet). Le backend
est détecté une seule fois par _detect_backend(), jamais deviné ailleurs.

Rotation (voir _apply_retention) : BACKUP_RETENTION_DAYS (config.py, défaut
30) supprime les sauvegardes plus anciennes que N jours ; un second filet de
sécurité (MAX_BACKUPS) borne aussi le nombre total au cas où plusieurs
sauvegardes seraient prises le même jour — le dossier backups/ ne grossit
jamais indéfiniment.
"""
import logging
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import config
import db

logger = logging.getLogger("backup_service")

# Filet de sécurité en plus de BACKUP_RETENTION_DAYS (jours) — voir docstring
# du module : "conserver les 30 dernières sauvegardes" au sens strict.
MAX_BACKUPS = 30

_FILENAME_PREFIX = "novamath_backup_"
_PRE_RESTORE_PREFIX = "pre_restore_"
_SQLITE_SUFFIX = ".sqlite3"
_POSTGRES_SUFFIX = ".sql"
# Microsecondes incluses : deux sauvegardes déclenchées coup sur coup (retry,
# tests) ne doivent jamais partager le même nom de fichier (voir _timestamp).
_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"


class BackupNotFound(Exception):
    """Levée par restore_backup() quand `filename` ne correspond à aucune
    sauvegarde existante — jamais une exception SQLite/OS brute qui
    laisserait deviner le layout disque du serveur."""


class BackupCorrupted(Exception):
    """Levée par restore_backup() quand le fichier de sauvegarde ne passe pas
    `PRAGMA integrity_check` — la restauration est annulée AVANT toute
    écriture dans db.DB_PATH, qui reste donc intact."""


def backup_dir():
    """Répertoire de sauvegarde (BACKUP_DIRECTORY, voir config.py — défaut
    backups/ à la racine du projet), créé automatiquement s'il n'existe pas
    encore (Partie 3 : "créer automatiquement un dossier backups/")."""
    path = Path(config.BACKUP_DIRECTORY)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _detect_backend():
    """'postgresql' si DATABASE_URL pointe vers un Postgres, 'sqlite' sinon
    (mode réel de ce projet aujourd'hui). Aucune autre partie du projet ne
    doit deviner le backend autrement que via cette fonction."""
    url = os.environ.get("DATABASE_URL", "")
    return "postgresql" if url.startswith(("postgres://", "postgresql://")) else "sqlite"


def _timestamp():
    return datetime.now(timezone.utc).strftime(_TIMESTAMP_FORMAT)


def _parse_timestamp_with_prefix(filename, prefix):
    """Horodatage encodé DANS LE NOM du fichier (pas sa date de dernière
    modification, insensible à une éventuelle copie/déplacement ultérieur).
    None si le nom ne correspond pas au format attendu pour ce préfixe."""
    stem = filename
    for suffix in (_SQLITE_SUFFIX, _POSTGRES_SUFFIX):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    if not stem.startswith(prefix):
        return None
    raw = stem[len(prefix):]
    try:
        return datetime.strptime(raw, _TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_timestamp(filename):
    return _parse_timestamp_with_prefix(filename, _FILENAME_PREFIX)


def _parse_pre_restore_timestamp(filename):
    """Symétrique de _parse_timestamp pour les copies de sécurité
    pre_restore_* (voir _pre_restore_safety_copy) — jamais confondues avec
    les sauvegardes normales (préfixe distinct), mais doivent tout de même
    pouvoir être identifiées pour être supprimées (delete_backup) ou purgées
    par rétention (_apply_retention_pre_restore_copies), sans quoi elles
    grossissent indéfiniment sur le volume de sauvegarde."""
    return _parse_timestamp_with_prefix(filename, _PRE_RESTORE_PREFIX)


def list_pre_restore_copies():
    """Symétrique de list_backups() pour les copies de sécurité pre_restore_*
    — jamais mélangées à la liste des sauvegardes normales (voir docstring de
    _apply_retention), afin de ne rien changer à l'affichage existant du
    panneau Administration (qui continue d'appeler list_backups())."""
    copies = []
    for path in backup_dir().iterdir():
        if not path.is_file():
            continue
        created_at = _parse_pre_restore_timestamp(path.name)
        if created_at is None:
            continue
        copies.append({
            "filename": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "created_at": created_at.isoformat(),
        })
    copies.sort(key=lambda b: b["created_at"], reverse=True)
    return copies


def backup_database():
    """Crée une sauvegarde horodatée de la base de données courante puis
    applique la rotation (voir _apply_retention). Renvoie le Path du fichier
    créé."""
    backend = _detect_backend()
    path = _backup_sqlite() if backend == "sqlite" else _backup_postgresql()
    logger.info("Sauvegarde créée : %s (%s octets).", path.name, path.stat().st_size)
    _apply_retention()
    return path


def _atomic_sqlite_copy(source_path, dest_path, tmp_path=None):
    """Copie `source_path` vers `dest_path` via l'API de sauvegarde native de
    sqlite3 (Connection.backup) plutôt qu'une simple copie de fichier : reste
    cohérente même si une autre connexion est ouverte sur la même base au même
    instant (verrouillage interne géré par SQLite lui-même).

    Écrite d'abord sous un nom temporaire, renommée vers son nom final
    UNIQUEMENT une fois l'écriture terminée (os.replace, atomique sur un même
    système de fichiers) : si le worker Gunicorn est tué (redéploiement,
    restart Fly.io) pendant l'écriture, le fichier final n'apparaît jamais —
    jamais de copie tronquée visible."""
    if tmp_path is None:
        tmp_path = dest_path.with_name(dest_path.name + ".tmp")
    source = sqlite3.connect(source_path)
    try:
        dest = sqlite3.connect(tmp_path)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    os.replace(tmp_path, dest_path)


def _backup_sqlite():
    dest_path = backup_dir() / f"{_FILENAME_PREFIX}{_timestamp()}{_SQLITE_SUFFIX}"
    _atomic_sqlite_copy(db.DB_PATH, dest_path)
    return dest_path


def _backup_postgresql():
    """Passe par l'exécutable `pg_dump` (jamais un SDK Python type psycopg,
    absent des dépendances du projet) — prêt à l'usage le jour où NovaMath
    migre vers Postgres (DATABASE_URL défini), non exercé en pratique
    aujourd'hui (voir _detect_backend). Lève RuntimeError si pg_dump échoue
    ou est introuvable, jamais une exception avalée silencieusement."""
    dest_path = backup_dir() / f"{_FILENAME_PREFIX}{_timestamp()}{_POSTGRES_SUFFIX}"
    database_url = os.environ.get("DATABASE_URL", "")
    try:
        with open(dest_path, "wb") as f:
            subprocess.run(["pg_dump", database_url], stdout=f, check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        dest_path.unlink(missing_ok=True)
        raise RuntimeError(f"Échec de la sauvegarde PostgreSQL (pg_dump) : {e}") from e
    return dest_path


def list_backups():
    """Sauvegardes existantes, la plus récente d'abord. Chaque entrée :
    {"filename", "path", "size_bytes", "created_at"} — created_at dérivé du
    nom de fichier (voir _parse_timestamp), jamais du système de fichiers."""
    backups = []
    for path in backup_dir().iterdir():
        if not path.is_file():
            continue
        created_at = _parse_timestamp(path.name)
        if created_at is None:
            continue
        backups.append({
            "filename": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "created_at": created_at.isoformat(),
        })
    backups.sort(key=lambda b: b["created_at"], reverse=True)
    return backups


def restore_backup(filename):
    """Restaure `filename` (voir list_backups()) par-dessus la base de
    données courante. Une copie de sécurité de l'état actuel est prise juste
    avant l'écrasement (voir _pre_restore_safety_copy, préfixe distinct —
    jamais comptée dans la rotation normale) : une restauration ratée ne
    doit jamais rendre l'état précédent irrécupérable."""
    source_path = backup_dir() / filename
    if not source_path.is_file() or _parse_timestamp(filename) is None:
        raise BackupNotFound(f"Sauvegarde introuvable : {filename!r}")

    backend = _detect_backend()
    if backend == "sqlite":
        _restore_sqlite(source_path)
    else:
        _restore_postgresql(source_path)
    logger.info("Base de données restaurée depuis %s.", filename)


def _pre_restore_safety_copy():
    """Copie de l'état actuel de la base AVANT écrasement par une
    restauration (voir _restore_sqlite) — utilise _atomic_sqlite_copy comme
    _backup_sqlite() (jamais shutil.copy2, qui ne copie que le fichier
    principal .db et peut omettre des pages déjà validées mais encore dans le
    .db-wal en mode WAL sous charge concurrente) : cohérente même avec des
    connexions actives au même instant."""
    if not Path(db.DB_PATH).exists():
        return
    dest_path = backup_dir() / f"{_PRE_RESTORE_PREFIX}{_timestamp()}{_SQLITE_SUFFIX}"
    _atomic_sqlite_copy(db.DB_PATH, dest_path)


def _validate_sqlite_integrity(path):
    """PRAGMA integrity_check sur `path` — lève BackupCorrupted si le fichier
    n'est pas une base SQLite saine (ex: sauvegarde tronquée par un kill en
    cours d'écriture avant ce correctif, ou fichier altéré). Appelée AVANT
    toute écriture dans db.DB_PATH : une sauvegarde corrompue ne doit jamais
    commencer à écraser la base de production."""
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise BackupCorrupted(f"Sauvegarde corrompue, restauration annulée : {exc}") from exc
    finally:
        conn.close()
    if not result or result[0] != "ok":
        raise BackupCorrupted(
            f"Sauvegarde corrompue, restauration annulée : {result[0] if result else 'vide'}"
        )


def _restore_sqlite(source_path):
    _validate_sqlite_integrity(source_path)
    _pre_restore_safety_copy()
    # Restaure vers un fichier temporaire puis remplace db.DB_PATH par un seul
    # os.replace atomique : si le process est tué (SIGKILL, restart Fly.io)
    # pendant la copie des pages, db.DB_PATH n'est JAMAIS partiellement
    # écrasé — soit l'ancienne base reste intacte (tmp jamais promu), soit la
    # nouvelle est en place en entier (tmp promu après écriture complète).
    tmp_path = Path(db.DB_PATH).with_name(Path(db.DB_PATH).name + ".restore_tmp")
    _atomic_sqlite_copy(source_path, Path(db.DB_PATH), tmp_path=tmp_path)


def _restore_postgresql(source_path):
    """Symétrique de _backup_postgresql : passe par `psql`, prêt à l'usage,
    non exercé en pratique tant qu'aucune connexion Postgres n'existe."""
    database_url = os.environ.get("DATABASE_URL", "")
    try:
        with open(source_path, "rb") as f:
            subprocess.run(["psql", database_url], stdin=f, check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        raise RuntimeError(f"Échec de la restauration PostgreSQL (psql) : {e}") from e


def delete_backup(filename):
    """Suppression MANUELLE d'une sauvegarde (module Administration ->
    Paramètres) — même validation que restore_backup() (BackupNotFound si le
    nom ne correspond à aucune sauvegarde réelle), jamais un chemin de
    fichier arbitraire accepté tel quel. Accepte aussi bien une sauvegarde
    normale qu'une copie de sécurité pre_restore_* (voir
    _pre_restore_safety_copy) : avant ce correctif, ces copies n'étaient
    reconnues par aucune validation ici et ne pouvaient donc jamais être
    supprimées via ce point d'entrée, même en connaissant leur nom exact.
    Distincte de _delete_backup_file() (interne, utilisée uniquement par
    _apply_retention() ci-dessous pour la rotation automatique, où un échec
    ponctuel est acceptable — il sera retenté à la prochaine sauvegarde) :
    ICI, un échec doit être signalé à l'administrateur qui vient de cliquer
    "Supprimer", jamais avalé silencieusement — d'où un appel direct à
    Path.unlink() (propage OSError) plutôt qu'une délégation à
    _delete_backup_file()."""
    path = backup_dir() / filename
    is_known = _parse_timestamp(filename) is not None or _parse_pre_restore_timestamp(filename) is not None
    if not path.is_file() or not is_known:
        raise BackupNotFound(f"Sauvegarde introuvable : {filename!r}")
    path.unlink()


def _apply_retention():
    """Supprime d'abord les sauvegardes plus anciennes que
    BACKUP_RETENTION_DAYS, puis, si plus de MAX_BACKUPS subsistent malgré
    tout (plusieurs sauvegardes le même jour), supprime les plus anciennes
    en excédent. Les copies de sécurité pre_restore_* (voir
    _pre_restore_safety_copy) ne sont jamais listées par list_backups() (donc
    jamais mélangées à l'affichage existant du panneau Administration), mais
    sont purgées séparément selon la même fenêtre de rétention — sans quoi
    elles grossiraient indéfiniment le volume de sauvegarde à chaque
    restauration (voir list_pre_restore_copies)."""
    backups = list_backups()
    cutoff_ts = datetime.now(timezone.utc).timestamp() - config.BACKUP_RETENTION_DAYS * 86400
    kept = []
    for b in backups:
        if datetime.fromisoformat(b["created_at"]).timestamp() < cutoff_ts:
            _delete_backup_file(b["path"])
        else:
            kept.append(b)
    for b in kept[MAX_BACKUPS:]:  # kept reste trié du plus récent au plus ancien
        _delete_backup_file(b["path"])
    for copy in list_pre_restore_copies():
        if datetime.fromisoformat(copy["created_at"]).timestamp() < cutoff_ts:
            _delete_backup_file(copy["path"])


def _delete_backup_file(path):
    try:
        Path(path).unlink()
        logger.info("Sauvegarde expirée supprimée : %s.", Path(path).name)
    except OSError as e:
        logger.warning("Impossible de supprimer la sauvegarde expirée %s : %s", path, e)

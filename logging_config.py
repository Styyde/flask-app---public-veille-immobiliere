# logging_config.py
"""Configuration centrale du logging applicatif.

A appeler une seule fois, au point d'entree du process (deja fait par
api/app.py au niveau module, donc couvre les 3 chemins d'entree reels :
main.py --mode web, main.py --mode desktop, et gunicorn --preload en
production). Idempotent : un second appel ne duplique pas les handlers.
Niveau ajustable via la variable d'environnement LOG_LEVEL (INFO par defaut),
sans toucher au code.

Renforcements par rapport a la version initiale (logging.basicConfig seul) :

1. Fichier de log tournant (5 Mo x 5), en plus de la console. Indispensable
   en mode desktop empaquete (--windowed) : il n'y a AUCUNE console attachee,
   donc sans fichier, toute erreur est invisible -- ni pour l'utilisateur, ni
   pour nous en support. Le dossier de logs est derive de config.DB_PATH
   (meme repertoire que la base de donnees), ce qui donne gratuitement le bon
   emplacement dans les 3 contextes : %LOCALAPPDATA%\\VeilleImmobiliere sur le
   desktop empaquete, /app/data en conteneur Docker (deja un volume monte,
   donc les logs survivent aux redemarrages), et flask-app/ en dev local.

2. Les print()/traceback.print_exc() existants (scraping, alembic...) sont
   dupliques vers ce meme fichier tournant, SANS toucher aux dizaines d'appels
   deja presents dans core/*.py, et sans jamais repasser par le dispatch
   `logging` standard : on ecrit directement sur le RotatingFileHandler
   (record construit a la main). C'est deliberement plus direct qu'un
   `logging.log()` classique -- ca evite tout risque d'interaction avec le
   StreamHandler console (observe en dev avec le reloader Werkzeug, qui
   provoquait une boucle stdout/stderr <-> logging). La console garde son
   flux d'origine, intact et jamais retouche (stdout reste actif pour
   Docker/Loki en production).

3. Toute exception non interceptee (thread principal ou secondaire) est
   loguee avant de faire planter l'app, plutot que de disparaitre en silence
   -- crucial en --windowed ou aucune boite de dialogue d'erreur ne s'affiche.
"""
import logging
import logging.handlers
import os
import sys
import threading

_configured = False


def _default_log_dir():
    try:
        import config
        return os.path.join(os.path.dirname(config.DB_PATH), 'logs')
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')


class _TeeToFileHandler:
    """Duplique un flux (stdout/stderr) vers un RotatingFileHandler, en
    ecrivant directement sur ce handler (bypass du dispatch `logging`
    standard/du root logger) pour ne jamais pouvoir boucler vers la console.
    Le flux d'origine continue de recevoir tout le texte, intact."""

    def __init__(self, original, file_handler, level, logger_name):
        self._original = original
        self._file_handler = file_handler
        self._level = level
        self._logger_name = logger_name
        self._buffer = ''

    def write(self, data):
        if self._original is not None:
            try:
                self._original.write(data)
            except Exception:
                pass
        self._buffer += data
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            if line.strip():
                self._emit(line)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass
        if self._buffer.strip():
            self._emit(self._buffer)
            self._buffer = ''

    def _emit(self, line):
        try:
            record = logging.LogRecord(
                self._logger_name, self._level, '', 0, line, None, None
            )
            self._file_handler.emit(record)
        except Exception:
            pass

    def isatty(self):
        return False

    def reconfigure(self, *args, **kwargs):
        if self._original is not None and hasattr(self._original, 'reconfigure'):
            self._original.reconfigure(*args, **kwargs)


def configure_logging(log_dir=None):
    global _configured
    if _configured:
        return
    level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    fmt = '%(asctime)s %(levelname)s [%(name)s] %(message)s'

    log_dir = log_dir or _default_log_dir()
    file_handler = None
    log_path = None
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'app.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
    except OSError:
        pass  # dossier non accessible en ecriture -> on garde au moins la console

    handlers = [logging.StreamHandler()]
    if file_handler is not None:
        handlers.append(file_handler)
    logging.basicConfig(level=level, format=fmt, handlers=handlers)
    _configured = True

    if file_handler is not None:
        if sys.stdout is not None:
            sys.stdout = _TeeToFileHandler(sys.stdout, file_handler, logging.INFO, 'stdout')
        if sys.stderr is not None:
            # WARNING (pas ERROR) : beaucoup de sorties routiniere (bannieres
            # de demarrage werkzeug/alembic) passent par stderr sans etre de
            # vraies erreurs -- WARNING les distingue quand meme des logs
            # applicatifs normaux (INFO, cote stdout) sans fausse alerte.
            sys.stderr = _TeeToFileHandler(sys.stderr, file_handler, logging.WARNING, 'stderr')

    def _log_uncaught(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger('uncaught').critical(
            "Exception non interceptee (thread principal)", exc_info=(exc_type, exc_value, exc_tb)
        )
    sys.excepthook = _log_uncaught

    def _log_uncaught_thread(args):
        logging.getLogger('uncaught').critical(
            "Exception non interceptee (thread %s)", args.thread.name if args.thread else '?',
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )
    threading.excepthook = _log_uncaught_thread

    logging.info("Logging initialise -- fichier : %s", log_path or '(indisponible, console uniquement)')

# main.py
import argparse
import sys


def _force_utf8_streams():
    """Sur Windows, stdout/stderr utilisent par défaut le codepage console
    (cp1252) : tout print() contenant un emoji ou un caractère hors cp1252
    (ex: core/runner.py, core/sarouty.py) lève une UnicodeEncodeError et fait
    planter la tâche en cours (scraping, migrations...). Corrige les deux
    modes (web et desktop) depuis ce point d'entrée commun."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


_force_utf8_streams()


def main():
    parser = argparse.ArgumentParser(description="Al Omrane Analyzer")
    parser.add_argument('--mode', choices=['web', 'desktop'], default='desktop',
                        help="Lancer en mode web (API Flask) ou desktop (fenêtre native affichant l'UI web)")
    args = parser.parse_args()

    if args.mode == 'web':
        from api.app import app
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        from desktop import run_desktop
        run_desktop()

if __name__ == '__main__':
    main()
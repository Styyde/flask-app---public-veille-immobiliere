# main.py
import sys
import argparse

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
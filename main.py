# main.py
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Al Omrane Analyzer")
    parser.add_argument('--mode', choices=['web', 'desktop'], default='desktop',
                        help="Lancer en mode web (API Flask) ou desktop (GUI PyQt)")
    args = parser.parse_args()
    
    if args.mode == 'web':
        from api import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        from gui import run_gui
        run_gui()

if __name__ == '__main__':
    main()
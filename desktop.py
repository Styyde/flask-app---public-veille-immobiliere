# desktop.py
# Version Desktop de l'application — encapsule l'interface web Flask dans une fenêtre PyQt6.
# Usage : py desktop.py
# Prérequis : pip install PyQt6 PyQt6-WebEngine

import sys
import os
import threading
import time
import socket

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplashScreen, QWidget, QVBoxLayout, QLabel
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont, QIcon


# ── Paramètres ──────────────────────────────────────────────────────────────
HOST = '127.0.0.1'
PORT = 5050        # Port distinct de debug Flask (5000) pour éviter les conflits
APP_TITLE = "Veille Immobilière — Maroc"
# ─────────────────────────────────────────────────────────────────────────────


def _find_free_port(preferred=PORT):
    """Retourne preferred si dispo, sinon un port libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((HOST, preferred)) != 0:
            return preferred
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _start_flask(port: int):
    """Lance Flask dans un thread daemon — sans rechargement automatique."""
    # On s'assure que le répertoire racine du projet est dans le path
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    from api.app import app as flask_app
    flask_app.run(host=HOST, port=port, debug=False, use_reloader=False, threaded=True)


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    """Attend que le serveur Flask soit prêt avant d'afficher la fenêtre."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


# ── Splash Screen ────────────────────────────────────────────────────────────

def _create_splash() -> QSplashScreen:
    """Crée un splash screen minimal pendant le chargement de Flask."""
    w, h = 480, 260
    pixmap = QPixmap(w, h)
    pixmap.fill(QColor("#0f172a"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Titre
    font_title = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#f1f5f9"))
    painter.drawText(0, 60, w, 60, Qt.AlignmentFlag.AlignHCenter, "🏙️  Veille Immobilière")

    # Sous-titre
    font_sub = QFont("Segoe UI", 11)
    painter.setFont(font_sub)
    painter.setPen(QColor("#94a3b8"))
    painter.drawText(0, 120, w, 40, Qt.AlignmentFlag.AlignHCenter, "Marché Immobilier Maroc")

    # Chargement
    font_load = QFont("Segoe UI", 10)
    painter.setFont(font_load)
    painter.setPen(QColor("#64748b"))
    painter.drawText(0, 200, w, 30, Qt.AlignmentFlag.AlignHCenter, "Démarrage de l'application…")

    painter.end()
    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    return splash


# ── Fenêtre principale ────────────────────────────────────────────────────────

class DesktopWindow(QMainWindow):
    def __init__(self, url: str):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)
        self._set_icon()

        # Widget central : WebEngineView
        self.browser = QWebEngineView()
        self.browser.setPage(QWebEnginePage(self.browser))
        self.browser.load(QUrl(url))

        # Barre de progression de chargement (optionnel, juste en haut)
        self.browser.loadFinished.connect(self._on_load_finished)

        self.setCentralWidget(self.browser)

    def _set_icon(self):
        """Cherche une icône PNG/ICO dans le dossier static, sinon ignore."""
        base = os.path.dirname(os.path.abspath(__file__))
        for candidate in ['static/favicon.ico', 'static/favicon.png', 'static/logo.png']:
            path = os.path.join(base, candidate)
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                break

    def _on_load_finished(self, ok: bool):
        if not ok:
            self.browser.setHtml("""
            <html><body style='background:#0f172a;color:#f1f5f9;font-family:Segoe UI;
                               display:flex;align-items:center;justify-content:center;
                               height:100vh;margin:0;font-size:18px;'>
              <div style='text-align:center;'>
                <div style='font-size:48px;'>⚠️</div>
                <p>Impossible de charger l'interface.</p>
                <p style='color:#64748b;font-size:14px;'>Vérifiez que Flask est bien démarré.</p>
              </div>
            </body></html>
            """)

    def closeEvent(self, event):
        """Quand on ferme la fenêtre, les threads Flask (daemon) s'arrêtent automatiquement."""
        event.accept()


# ── Point d'entrée ─────────────────────────────────────────────────────────

def run_desktop():
    port = _find_free_port(PORT)
    url = f"http://{HOST}:{port}"

    # 1. Lancer Flask dans un thread daemon (s'arrête quand l'app Qt se ferme)
    flask_thread = threading.Thread(target=_start_flask, args=(port,), daemon=True)
    flask_thread.start()

    # 2. Démarrer Qt
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_TITLE)
    qt_app.setOrganizationName("VeilleImmo")

    # 3. Afficher le splash le temps que Flask démarre
    splash = _create_splash()
    splash.show()
    qt_app.processEvents()

    # 4. Attendre que le serveur soit prêt (dans un QTimer pour ne pas bloquer l'UI)
    ready = [False]

    def check_server():
        if _wait_for_server(port, timeout=20):
            ready[0] = True
        else:
            ready[0] = None   # timeout

    server_thread = threading.Thread(target=check_server, daemon=True)
    server_thread.start()

    # Boucle Qt pendant que le serveur démarre
    while server_thread.is_alive():
        qt_app.processEvents()
        time.sleep(0.05)

    if not ready[0]:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Erreur de démarrage",
            f"Le serveur Flask n'a pas pu démarrer sur le port {port}.\n"
            "Vérifiez qu'il n'y a pas de conflit de port."
        )
        sys.exit(1)

    # 5. Ouvrir la fenêtre principale et fermer le splash
    window = DesktopWindow(url)
    window.show()
    splash.finish(window)

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    run_desktop()

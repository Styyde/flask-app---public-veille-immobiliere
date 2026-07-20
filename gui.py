# gui.py
import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QDoubleSpinBox,
    QTabWidget, QGroupBox
)
from PyQt6.QtCore import Qt
from filters import get_filtered_data, get_statistiques_globales

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analyse Al Omrane")
        self.setGeometry(100, 100, 1200, 700)
        self.initUI()
        self.load_stats()
    
    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Onglets
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Onglet Filtrage
        filter_tab = QWidget()
        self.tabs.addTab(filter_tab, "Filtrage")
        filter_layout = QVBoxLayout(filter_tab)
        
        # Ligne de filtres
        filters_group = QGroupBox("Filtres")
        filter_layout.addWidget(filters_group)
        filters_grid = QVBoxLayout(filters_group)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Budget min (DH):"))
        self.budget_min = QDoubleSpinBox()
        self.budget_min.setRange(0, 100000000)
        self.budget_min.setSingleStep(100000)
        row1.addWidget(self.budget_min)
        
        row1.addWidget(QLabel("Budget max (DH):"))
        self.budget_max = QDoubleSpinBox()
        self.budget_max.setRange(0, 100000000)
        self.budget_max.setSingleStep(100000)
        self.budget_max.setValue(10000000)
        row1.addWidget(self.budget_max)
        
        row1.addWidget(QLabel("Ville:"))
        self.ville_combo = QComboBox()
        self.ville_combo.addItem("Toutes")
        row1.addWidget(self.ville_combo)
        
        row1.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Tous")
        row1.addWidget(self.type_combo)
        filters_grid.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Badge:"))
        self.badge_combo = QComboBox()
        self.badge_combo.addItem("Tous")
        row2.addWidget(self.badge_combo)
        
        row2.addWidget(QLabel("Étage:"))
        self.etage_combo = QComboBox()
        self.etage_combo.addItem("Tous")
        row2.addWidget(self.etage_combo)
        
        row2.addWidget(QLabel("Prix/m² min:"))
        self.prix_m2_min = QDoubleSpinBox()
        self.prix_m2_min.setRange(0, 100000)
        self.prix_m2_min.setSingleStep(100)
        row2.addWidget(self.prix_m2_min)
        
        row2.addWidget(QLabel("Prix/m² max:"))
        self.prix_m2_max = QDoubleSpinBox()
        self.prix_m2_max.setRange(0, 100000)
        self.prix_m2_max.setSingleStep(100)
        self.prix_m2_max.setValue(50000)
        row2.addWidget(self.prix_m2_max)
        filters_grid.addLayout(row2)
        
        # Bouton Rechercher
        search_btn = QPushButton("Rechercher")
        search_btn.clicked.connect(self.search)
        filter_layout.addWidget(search_btn)
        
        # Tableau des résultats
        self.table = QTableWidget()
        filter_layout.addWidget(self.table)
        
        # Onglet Statistiques
        stats_tab = QWidget()
        self.tabs.addTab(stats_tab, "Statistiques")
        stats_layout = QVBoxLayout(stats_tab)
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
    
    def load_stats(self):
        # Charger les valeurs des listes déroulantes
        stats = get_statistiques_globales()
        self.ville_combo.addItems(stats.get('villes', []))
        self.type_combo.addItems(stats.get('types_biens', []))
        self.badge_combo.addItems(stats.get('badges', []))
        self.etage_combo.addItems(stats.get('etages', []))
        
        # Afficher les stats
        text = f"<b>Projets :</b> {stats.get('nb_projets',0)}  "
        text += f"<b>Lots :</b> {stats.get('nb_lots',0)}  "
        text += f"<b>Produits :</b> {stats.get('nb_produits',0)}  "
        text += f"<b>Villes :</b> {', '.join(stats.get('villes', []))}"
        self.stats_label.setText(text)
    
    def search(self):
        ville = self.ville_combo.currentText()
        type_bien = self.type_combo.currentText()
        badge = self.badge_combo.currentText()
        etage = self.etage_combo.currentText()
        # Si "Tous/Toutes", on passe None
        ville = None if ville == "Toutes" else ville
        type_bien = None if type_bien == "Tous" else type_bien
        badge = None if badge == "Tous" else badge
        etage = None if etage == "Tous" else etage
        
        df = get_filtered_data(
            budget_min=self.budget_min.value() if self.budget_min.value() > 0 else None,
            budget_max=self.budget_max.value() if self.budget_max.value() > 0 else None,
            ville=ville,
            type_bien=type_bien,
            badge=badge,
            etage=etage,
            prix_m2_min=self.prix_m2_min.value() if self.prix_m2_min.value() > 0 else None,
            prix_m2_max=self.prix_m2_max.value() if self.prix_m2_max.value() > 0 else None
        )
        self.display_table(df)
    
    def display_table(self, df):
        self.table.setRowCount(0)
        if df.empty:
            return
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()

def run_gui():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    run_gui()
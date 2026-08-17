# email_sender/sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from analytics.scorer import get_top_opportunities_for_email

# ============================================================
# ⚙️ CONFIGURATION EMAIL - À MODIFIER AVEC VOS IDENTIFIANTS
# ============================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "votre.email@gmail.com"
EMAIL_PASSWORD = "votre_mot_de_passe_app"  # Utiliser un mot de passe d'application
EMAIL_RECIPIENT = "directeur@entreprise.com"
EMAIL_RECIPIENT_CC = ""  # Optionnel: ajouter un CC

def generer_rapport_html(opportunites, limit=10):
    """Génère un rapport HTML des opportunités."""
    top = opportunites[:limit] if len(opportunites) >= limit else opportunites
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport opportunités Al Omrane</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #1a5276; border-bottom: 3px solid #2e86c1; padding-bottom: 10px; }}
            h2 {{ color: #2e86c1; }}
            .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
            th {{ background-color: #2874a6; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .opportunite {{ background-color: #d5f5e3; }}
            .badge {{ 
                background-color: #f39c12; 
                color: white; 
                padding: 3px 10px; 
                border-radius: 12px; 
                font-size: 11px;
                display: inline-block;
            }}
            .prix_m2 {{ font-weight: bold; color: #1a5276; }}
            .footer {{ margin-top: 30px; color: #7f8c8d; font-size: 12px; border-top: 1px solid #ddd; padding-top: 15px; }}
            .stat {{
                display: inline-block;
                background-color: #eaf2f8;
                padding: 10px 20px;
                border-radius: 8px;
                margin-right: 15px;
            }}
            .stat .nombre {{
                font-size: 24px;
                font-weight: bold;
                color: #1a5276;
            }}
        </style>
    </head>
    <body>
        <h1>🏗️ Rapport des Opportunités Al Omrane</h1>
        
        <div class="header">
            <p><strong>📅 Date :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <p><strong>📊 Total d'opportunités identifiées :</strong> {len(opportunites)}</p>
            <div>
                <span class="stat"><span class="nombre">{len([o for o in opportunites if o['est_opportunite']])}</span> 🔥 Meilleures affaires</span>
                <span class="stat"><span class="nombre">{len(opportunites)}</span> 📋 Produits analysés</span>
            </div>
        </div>
        
        <h2>🏆 Top {limit} des meilleures affaires</h2>
        <table>
            <tr>
                <th>#</th>
                <th>Projet</th>
                <th>Localisation</th>
                <th>Type</th>
                <th>Lot</th>
                <th>N° Produit</th>
                <th>Surface</th>
                <th>Prix</th>
                <th>Prix/m²</th>
                <th>Moyenne</th>
                <th>Écart</th>
            </tr>
    """
    
    for i, p in enumerate(top, 1):
        classe = "opportunite" if p['est_opportunite'] else ""
        badge = f"<span class='badge'>{p['badge']}</span>" if p['badge'] else ""
        
        html += f"""
            <tr class="{classe}">
                <td><strong>{i}</strong></td>
                <td><strong>{p['titre']}</strong><br><small>{badge}</small></td>
                <td>{p['localisation']}</td>
                <td>{p['type_bien']}</td>
                <td style="font-size: 11px;">{p['lot_titre'][:30]}</td>
                <td>{p['no_produit']}</td>
                <td>{p['surface']:.0f} m²</td>
                <td>{p['prix']:,.0f} DH</td>
                <td class="prix_m2">{p['prix_m2']:,.2f} DH/m²</td>
                <td>{p['moyenne_groupe']:,.2f} DH/m²</td>
                <td style="color: {'#27ae60' if p['ecart_pourcent'] < 0 else '#e74c3c'};">
                    {p['ecart_pourcent']:.1f}%
                </td>
            </tr>
        """
    
    html += """
        </table>
        
        <div class="footer">
            <p>📌 Ce rapport a été généré automatiquement par le système de veille Al Omrane.</p>
            <p>💡 Les opportunités sont identifiées par un écart de prix/m² par rapport à la moyenne de la catégorie (ville + type de bien).</p>
        </div>
    </body>
    </html>
    """
    
    return html

def envoyer_rapport_email(limit=10, recipient=None):
    """
    Envoie le rapport des opportunités par email.
    
    Args:
        limit (int): Nombre d'opportunités à inclure
        recipient (str): Email du destinataire (si différent de EMAIL_RECIPIENT)
    """
    opportunites = get_top_opportunities_for_email(limit)
    
    if not opportunites:
        print("⚠️ Aucune opportunité trouvée. Email non envoyé.")
        return
    
    html = generer_rapport_html(opportunites, limit)
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📊 Rapport opportunités Al Omrane - {datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient or EMAIL_RECIPIENT
    if EMAIL_RECIPIENT_CC:
        msg['Cc'] = EMAIL_RECIPIENT_CC
    
    # Version texte simple (fallback)
    texte_simple = f"Rapport des opportunités Al Omrane du {datetime.now().strftime('%d/%m/%Y')}\n"
    for i, p in enumerate(opportunites[:limit], 1):
        texte_simple += f"\n{i}. {p['titre']} - {p['localisation']} - {p['prix_m2']:.2f} DH/m²"
    
    partie_texte = MIMEText(texte_simple, 'plain')
    partie_html = MIMEText(html, 'html')
    
    msg.attach(partie_texte)
    msg.attach(partie_html)
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        destinataires = recipient or EMAIL_RECIPIENT
        if EMAIL_RECIPIENT_CC:
            destinataires += f" (CC: {EMAIL_RECIPIENT_CC})"
        print(f"✅ Email envoyé à {destinataires}")
        return True
    except Exception as e:
        print(f"❌ Erreur d'envoi d'email : {e}")
        return False

def envoyer_rapport_test():
    """Envoie un email de test."""
    print("📧 Test d'envoi d'email...")
    from analytics.scorer import identifier_opportunites
    opportunites = identifier_opportunites()
    if opportunites:
        envoyer_rapport_email(limit=5)
    else:
        print("⚠️ Aucune donnée pour l'email. Lancez d'abord le scraping.")

if __name__ == "__main__":
    envoyer_rapport_test()
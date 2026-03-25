import streamlit as st
import pandas as pd
import sqlite3
import hmac
import json
import os
from datetime import datetime
from typing import Optional, Tuple

# ========================
#  KONFIGURATION & KONSTANTEN
# ========================
DB_FILE = "it_inventory_final.db"
PASSWORDS = {"admin": "admin123", "tech": "tech123", "procure": "procure123"}

# Preisvorschläge für Beschaffung (Suchschlüssel -> Preis)
PRICE_REFERENCE = {
    "ThinkPad": 1650.0, "MacBook Pro": 2499.0, "Dell XPS": 1850.0,
    "HP EliteBook": 1350.0, "Surface Laptop": 1450.0, "Asus ROG": 1700.0,
    "Lenovo ThinkStation": 2100.0, "Dell PowerEdge": 5400.0, "HP ZBook": 2800.0,
    "Yoga 9i": 1550.0, "Mac Studio": 2299.0, "Wacom Cintiq": 2550.0,
    "Eizo ColorEdge": 4800.0, "BenQ PD": 1150.0, "Apple Pro Display": 5500.0,
    "Dell UltraSharp": 850.0, "Asus ProArt": 3200.0, "LG UltraFine": 1200.0,
    "Eizo FlexScan": 1400.0, "iPhone 15": 1199.0, "Samsung Galaxy S23": 950.0,
    "Google Pixel": 899.0, "OnePlus": 750.0, "Sony Xperia": 1100.0,
    "Huawei P50": 850.0, "Xiaomi Mi": 900.0, "Oppo Find": 950.0,
    "Asus ROG Phone": 1050.0, "Zebra L10": 2850.0, "Advantech Panel": 1950.0,
    "Datalogic": 450.0, "Honeywell Dolphin": 1350.0, "Intermec CK3X": 1100.0,
    "Panasonic Toughbook": 3200.0, "CipherLab": 650.0, "Denso BHT": 1250.0,
    "Zebra MC33": 1450.0, "Fujitsu Belegscanner": 480.0, "Brother HL": 199.0,
    "HP LaserJet": 350.0, "Epson WorkForce": 220.0, "Canon imageCLASS": 280.0,
    "Lexmark B": 310.0, "Samsung Xpress": 180.0, "Ricoh SP": 240.0, "Kyocera ECOSYS": 420.0
}

# ========================
#  DATENBANK HELFER
# ========================
def get_connection() -> sqlite3.Connection:
    """Liefert eine SQLite-Verbindung zur Datenbank."""
    return sqlite3.connect(DB_FILE)

def init_database() -> None:
    """Erstellt alle Tabellen, falls sie nicht existieren, und befüllt sie mit Beispieldaten."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Inventar-Tabelle
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id TEXT PRIMARY KEY,
            typ TEXT,
            abteilung TEXT,
            status TEXT,
            besitzer TEXT,
            last_update TEXT,
            seriennummer TEXT,
            garantie_bis TEXT,
            details_json TEXT
        )''')

        # Service-Tabelle
        cursor.execute('''CREATE TABLE IF NOT EXISTS services (
            id TEXT PRIMARY KEY,
            name TEXT,
            beschreibung TEXT,
            zielgruppe TEXT,
            status TEXT,
            standard_dauer TEXT
        )''')

        # Anfrage-Tabelle
        cursor.execute('''CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anfrager TEXT,
            abteilung TEXT,
            typ TEXT,
            referenz_id TEXT,
            status TEXT,
            erstellt_am TEXT,
            letzte_aenderung TEXT,
            kommentar TEXT,
            preis REAL
        )''')

        # Beispieldaten für Services und Inventar, falls leer
        _init_sample_services(cursor)
        _init_sample_inventory(cursor)

        conn.commit()
    finally:
        conn.close()

def _init_sample_services(cursor: sqlite3.Cursor) -> None:
    """Fügt Beispieldienste ein, falls die Services-Tabelle leer ist."""
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        sample_services = [
            # Allgemeine Services (Zielgruppe "Alle")
            ("SVC-001", "Adobe Creative Cloud", "Installation & Lizenz", "Alle", "aktiv", "2 Tage"),
            ("SVC-002", "VPN-Zugang", "Einrichtung Homeoffice", "Alle", "aktiv", "1 Tag"),
            ("SVC-003", "Software-Lizenz", "Verwaltung von Softwarelizenzen", "Alle", "aktiv", "1 Tag"),
            ("SVC-004", "IT-Support", "Allgemeine IT-Unterstützung", "Alle", "aktiv", "1 Tag"),
            ("SVC-005", "Schulungen", "IT-Schulungen für Mitarbeiter", "Alle", "aktiv", "Variabel"),
            ("SVC-006", "Sicherheitsüberprüfung", "IT-Sicherheitsaudit", "Alle", "aktiv", "4 Tage"),
            ("SVC-007", "Geräteentsorgung", "Sichere Entsorgung von Altgeräten", "Alle", "aktiv", "2 Tage"),
            ("SVC-008", "Software-Update", "Regelmäßige Softwareaktualisierungen", "Alle", "aktiv", "1 Tag"),
            ("SVC-009", "Passwort-Reset", "Zurücksetzen von Passwörtern", "Alle", "aktiv", "1 Tag"),
            ("SVC-010", "IT-Beratung", "Beratung zu IT-Anschaffungen", "Alle", "aktiv", "Variabel"),
            # IT spezifisch
            ("SVC-011", "Datenrettung", "Wiederherstellung verlorener Daten", "IT", "aktiv", "5 Tage"),
            ("SVC-012", "Hardware-Upgrade", "Aufrüstung bestehender Hardware", "IT", "aktiv", "7 Tage"),
            ("SVC-013", "Netzwerk-Setup", "Einrichtung von Netzwerken", "IT", "aktiv", "3 Tage"),
            ("SVC-014", "Cloud-Migration", "Unterstützung bei Cloud-Umzug", "IT", "aktiv", "10 Tage"),
            # Vertrieb
            ("SVC-015", "Notebook-Setup", "Grundkonfiguration", "Vertrieb", "aktiv", "3 Tage"),
            # Logistik
            ("SVC-016", "Lager-WLAN-Check", "Signalstärkenmessung für Scanner", "Logistik", "aktiv", "1 Tag"),
            ("SVC-017", "Scanner-Konfiguration", "Anbindung an das ERP-System", "Logistik", "aktiv", "2 Std"),
            # Buchhaltung
            ("SVC-018", "DATEV-Support", "Update & Schnittstellenprüfung", "Buchhaltung", "aktiv", "1 Tag"),
            ("SVC-019", "Archiv-Migration", "Digitale Belegarchivierung Setup", "Buchhaltung", "aktiv", "5 Tage")
        ]
        cursor.executemany("INSERT INTO services VALUES (?,?,?,?,?,?)", sample_services)

def _init_sample_inventory(cursor: sqlite3.Cursor) -> None:
    """Fügt Beispieldaten in die Inventartabelle ein, falls diese leer ist."""
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        tech_srv = '{"IP": "192.168.10.15", "OS": "Ubuntu 22.04", "CPU": "2x Xeon", "RAM": "128GB"}'
        tech_tablet = '{"IP": "DHCP", "Schutzklasse": "IP65", "Display": "Glove-Touch", "Akku": "12h"}'
        tech_panel = '{"OS": "Win10 IoT", "Montage": "VESA 100", "Kühlung": "Passiv", "Anschlüsse": "RS232"}'

        sample_assets = [
            # IT-Abteilung
            ("HW-IT-001", "ThinkPad X1 Carbon", "IT", "Lager", "-", "-", "SN-9921-X1", "01.2027", '{"RAM": "16GB"}'),
            ("HW-IT-002", "Dell PowerEdge R740", "IT", "In Benutzung", "Admin", "25.03.2026", "SRV-DELL-01", "12.2028", tech_srv),
            ("HW-IT-003", "HP EliteBook 840", "IT", "In Benutzung", "Mitarbeiter A", "10.01.2024", "SN-HP-840-55", "03.2025", '{"RAM": "8GB"}'),
            ("HW-IT-004", "Lenovo ThinkStation P360", "IT", "Lager", "-", "-", "SN-LEN-P360-77", "11.2026", '{"GPU": "NVIDIA RTX A2000"}'),
            ("HW-IT-005", "Apple MacBook Pro 16", "IT", "Lager", "-", "-", "SN-APPLE-MBP16-99", "08.2027", '{"CPU": "M1 Pro"}'),
            ("HW-IT-006", "Asus ROG Zephyrus G14", "IT", "In Benutzung", "Mitarbeiter D", "05.04.2024", "SN-ASUS-G14-88", "04.2025", '{"GPU": "NVIDIA RTX 3060"}'),
            ("HW-IT-007", "Microsoft Surface Laptop 4", "IT", "In Benutzung", "Mitarbeiter E", "12.04.2024", "SN-MS-SURFACE-44", "05.2025", '{"RAM": "16GB"}'),
            ("HW-IT-008", "Dell XPS 15", "IT", "Lager", "-", "-", "SN-DELL-XPS15-33", "07.2027", '{"CPU": "Intel i7"}'),
            ("HW-IT-009", "HP ZBook Studio G8", "IT", "Lager", "-", "-", "SN-HP-ZBOOK-G8-66", "06.2025", '{"GPU": "NVIDIA RTX A5000"}'),
            ("HW-IT-010", "Lenovo Yoga 9i", "IT", "Lager", "-", "-", "SN-LEN-YOGA9I-22", "09.2026", '{"Display": "4K Touchscreen"}'),
            # Grafik
            ("HW-GR-001", "Mac Studio (M2)", "Grafik", "Lager", "-", "-", "APPLE-M2-088", "06.2027", '{"GPU": "30 Core"}'),
            ("HW-GR-002", "Wacom Cintiq Pro 24", "Grafik", "In Benutzung", "Mitarbeiter B", "15.02.2024", "SN-WACOM-CINTIQ-24", "02.2025", '{"Druckstufen": "8192"}'),
            ("HW-GR-003", "Eizo ColorEdge CG319X", "Grafik", "Lager", "-", "-", "SN-EIZO-CG319X-66", "09.2026", '{"Auflösung": "4096x2160"}'),
            ("HW-GR-004", "BenQ PD3220U", "Grafik", "In Benutzung", "Mitarbeiter F", "18.02.2024", "SN-BENQ-PD3220U-22", "01.2025", '{"Farbgenauigkeit": "99% AdobeRGB"}'),
            ("HW-GR-005", "Apple Pro Display XDR", "Grafik", "Lager", "-", "-", "SN-APPLE-PRODISP-XDR-55", "10.2027", '{"Helligkeit": "1600 nits"}'),
            ("HW-GR-006", "Dell UltraSharp U2723QE", "Grafik", "In Benutzung", "Mitarbeiter H", "22.02.2024", "SN-DELL-U2723QE-44", "03.2025", '{"Konnektivität": "USB-C"}'),
            ("HW-GR-007", "Asus ProArt PA32UCX", "Grafik", "Lager", "-", "-", "SN-ASUS-PA32UCX-77", "12.2026", '{"HDR": "HDR10"}'),
            ("HW-GR-008", "LG UltraFine 5K", "Grafik", "In Benutzung", "Mitarbeiter I", "28.02.2024", "SN-LG-ULTRAFINE-5K-33", "02.2025", '{"Auflösung": "5120x2880"}'),
            ("HW-GR-009", "Eizo FlexScan EV3895", "Grafik", "Lager", "-", "-", "SN-EIZO-FLEXSCAN-3895-66", "11.2026", '{"Seitenverhältnis": "21:9"}'),
            ("HW-GR-010", "BenQ EX3501R", "Grafik", "In Benutzung", "Mitarbeiter J", "05.03.2024", "SN-BENQ-EX3501R-22", "01.2025", '{"Curved": "1800R"}'),
            # Vertrieb
            ("HW-VT-001", "iPhone 15 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-334455", "10.2026", '{"MDM": "Active"}'),
            ("HW-VT-002", "Samsung Galaxy S23", "Vertrieb", "In Benutzung", "Mitarbeiter C", "20.03.2024", "IMEI-556677", "09.2026", '{"MDM": "Active"}'),
            ("HW-VT-003", "Google Pixel 7 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-778899", "12.2026", '{"MDM": "Active"}'),
            ("HW-VT-004", "OnePlus 11", "Vertrieb", "In Benutzung", "Mitarbeiter G", "25.03.2024", "IMEI-990011", "11.2026", '{"MDM": "Active"}'),
            ("HW-VT-005", "Sony Xperia 1 IV", "Vertrieb", "Lager", "-", "-", "IMEI-112233", "09.2026", '{"MDM": "Active"}'),
            ("HW-VT-006", "Huawei P50 Pro", "Vertrieb", "In Benutzung", "Mitarbeiter K", "30.03.2024", "IMEI-445566", "08.2026", '{"MDM": "Active"}'),
            ("HW-VT-007", "Xiaomi Mi 11 Ultra", "Vertrieb", "Lager", "-", "-", "IMEI-667788", "11.2026", '{"MDM": "Active"}'),
            ("HW-VT-008", "Oppo Find X5 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-889900", "10.2026", '{"MDM": "Active"}'),
            ("HW-VT-009", "Asus ROG Phone 6", "Vertrieb", "Lager", "-", "-", "IMEI-223344", "10.2026", '{"MDM": "Active"}'),
            ("HW-VT-010", "Realme GT 2 Pro", "Vertrieb", "In Benutzung", "Mitarbeiter M", "15.04.2024", "IMEI-334422", "09.2026", '{"MDM": "Active"}'),
            # Logistik
            ("HW-LOG-001", "Zebra L10 Rugged Tablet", "Logistik", "Lager", "-", "-", "SN-ZEB-990", "12.2026", tech_tablet),
            ("HW-LOG-002", "Advantech Panel-PC 15\"", "Logistik", "Lager", "-", "-", "SN-ADV-P15", "05.2027", tech_panel),
            ("HW-LOG-003", "Datalogic Handscanner", "Logistik", "In Benutzung", "Lagerhalle Süd", "12.03.2026", "SN-DL-SCAN-01", "08.2026", '{"Typ": "2D-Imager"}'),
            ("HW-LOG-004", "Honeywell Dolphin CT60", "Logistik", "In Benutzung", "Lagerhalle Nord", "30.01.2026", "SN-HONEY-DOLPHIN", "07.2026", '{"Betriebssystem": "Android 11"}'),
            ("HW-LOG-005", "Intermec CK3X", "Logistik", "Lager", "-", "-", "SN-INT-CK3X", "09.2026", '{"Akkulaufzeit": "14h"}'),
            ("HW-LOG-006", "Panasonic Toughbook FZ-N1", "Logistik", "In Benutzung", "Versand", "15.02.2026", "SN-PANA-TOUGHBOOK", "06.2026", '{"Display": "4.7 Zoll"}'),
            ("HW-LOG-007", "CipherLab RS31", "Logistik", "Lager", "-", "-", "SN-CIPHER-RS31", "11.2026", '{"Konnektivität": "4G LTE"}'),
            ("HW-LOG-008", "Denso BHT-1700", "Logistik", "In Benutzung", "Wareneingang", "20.03.2026", "SN-DENSO-BHT1700", "05.2026", '{"Scanner": "1D Laser"}'),
            ("HW-LOG-009", "Zebra MC3300", "Logistik", "Lager", "-", "-", "SN-ZEB-MC3300", "10.2026", '{"Betriebssystem": "Android 10"}'),
            ("HW-LOG-010", "Honeywell Granit 1980i", "Logistik", "In Benutzung", "Lagerhalle Ost", "28.01.2026", "SN-HONEY-GRANIT", "08.2026", '{"Schutzklasse": "IP67"}'),
            # Buchhaltung
            ("HW-ACC-001", "Fujitsu Belegscanner ix1600", "Buchhaltung", "Lager", "-", "-", "SN-FUJ-SCAN-01", "03.2027", '{"Speed": "40ppm"}'),
            ("HW-ACC-002", "Dell UltraSharp Dual-Set", "Buchhaltung", "In Benutzung", "Finanzabteilung", "05.01.2026", "SN-DELL-DUAL", "11.2026", '{"Zoll": "2x 27"}'),
            ("HW-ACC-003", "Brother HL-L2350DW Drucker", "Buchhaltung", "In Benutzung", "Büro", "10.02.2026", "SN-BROTHER-HL2350", "09.2026", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-004", "HP LaserJet Pro M404dn", "Buchhaltung", "In Benutzung", "Büro", "18.03.2026", "SN-HP-M404DN", "10.2026", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-005", "Epson WorkForce Pro WF-3720", "Buchhaltung", "Lager", "-", "-", "SN-EPSON-WF3720", "04.2027", '{"Drucktechnologie": "Tintenstrahl"}'),
            ("HW-ACC-006", "Canon imageCLASS LBP6230dw", "Buchhaltung", "In Benutzung", "Büro", "25.01.2026", "SN-CANON-LBP6230", "08.2026", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-007", "Lexmark B2236dw", "Buchhaltung", "Lager", "-", "-", "SN-LEXMARK-B2236", "07.2027", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-008", "Samsung Xpress M2020W", "Buchhaltung", "In Benutzung", "Büro", "12.02.2026", "SN-SAMSUNG-M2020W", "09.2026", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-009", "Ricoh SP 150SUw", "Buchhaltung", "Lager", "-", "-", "SN-RICOH-SP150SUW", "06.2027", '{"Drucktechnologie": "Laser"}'),
            ("HW-ACC-010", "Kyocera ECOSYS P2040dn", "Buchhaltung", "In Benutzung", "Büro", "30.03.2026", "SN-KYOCERA-P2040DN", "08.2026", '{"Drucktechnologie": "Laser"}')
        ]
        cursor.executemany("INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?,?)", sample_assets)

def load_inventory() -> pd.DataFrame:
    """Lädt die gesamte Inventartabelle als DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM inventory", conn)
    finally:
        conn.close()

def load_requests_by_status(status: str) -> pd.DataFrame:
    """Lädt Anfragen mit einem bestimmten Status."""
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM requests WHERE status = ?", conn, params=(status,))
    finally:
        conn.close()

def load_services_for_department(department: str) -> pd.DataFrame:
    """Lädt Services, die für eine Abteilung oder 'Alle' verfügbar sind."""
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM services WHERE zielgruppe IN (?, 'Alle')", conn, params=(department,))
    finally:
        conn.close()

def load_user_requests(user_name: str, limit: int = 5) -> pd.DataFrame:
    """Lädt die letzten Anfragen eines Benutzers."""
    conn = get_connection()
    try:
        return pd.read_sql("""
            SELECT typ, referenz_id, status, erstellt_am
            FROM requests
            WHERE anfrager = ?
            ORDER BY erstellt_am DESC LIMIT ?
        """, conn, params=(user_name, limit))
    finally:
        conn.close()

def load_budget_stats() -> Tuple[float, pd.DataFrame]:
    """Lädt die Gesamtausgaben und die nach Abteilung gruppierten Ausgaben für 'In Bestellung'."""
    conn = get_connection()
    try:
        total = pd.read_sql("SELECT SUM(preis) FROM requests WHERE status = 'In Bestellung'", conn).iloc[0,0] or 0.0
        by_dept = pd.read_sql("""
            SELECT abteilung, SUM(preis) as total
            FROM requests
            WHERE status = 'In Bestellung'
            GROUP BY abteilung
        """, conn)
        return total, by_dept
    finally:
        conn.close()

def add_request(anfrager: str, abteilung: str, typ: str, referenz_id: str) -> None:
    """Fügt eine neue Anfrage (offen) in die Datenbank ein."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am)
            VALUES (?,?,?,?,'offen',?)
        """, (anfrager, abteilung, typ, referenz_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
    finally:
        conn.close()

def approve_request(request_id: int, asset_anfrager: Optional[str] = None) -> None:
    """Genehmigt eine Anfrage und aktualisiert ggf. den Besitzer des Assets."""
    conn = get_connection()
    try:
        conn.execute("UPDATE requests SET status = 'genehmigt' WHERE id = ?", (request_id,))
        # Falls es sich um ein Asset handelt, Besitzer ändern
        if asset_anfrager:
            conn.execute("""
                UPDATE inventory
                SET status = 'In Benutzung', besitzer = ?, last_update = ?
                WHERE id = ?
            """, (asset_anfrager, datetime.now().strftime("%d.%m.%Y"), asset_anfrager))
        conn.commit()
    finally:
        conn.close()

def mark_for_procurement(request_id: int) -> None:
    """Setzt den Status einer Anfrage auf 'Einkauf prüfen'."""
    conn = get_connection()
    try:
        conn.execute("UPDATE requests SET status = 'Einkauf prüfen' WHERE id = ?", (request_id,))
        conn.commit()
    finally:
        conn.close()

def order_item(request_id: int, price: float) -> None:
    """Bestellt ein Gerät, setzt Status auf 'In Bestellung' und speichert Preis."""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE requests
            SET status = 'In Bestellung',
                preis = ?,
                kommentar = 'Bestellt am ' || ?
            WHERE id = ?
        """, (price, datetime.now().strftime("%d.%m.%Y"), request_id))
        conn.commit()
    finally:
        conn.close()

def clear_requests_and_reset_inventory() -> None:
    """Löscht alle Anfragen und setzt den Inventarstatus zurück (für Wartung)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM requests")
        conn.execute("UPDATE inventory SET status = 'Lager', besitzer = '-', last_update = '-'")
        conn.commit()
    finally:
        conn.close()

def add_asset(asset_id: str, model: str, department: str, serial: str, warranty: str) -> None:
    """Fügt ein neues Asset in die Datenbank ein."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO inventory VALUES (?,?,?, 'Lager', '-', '-', ?, ?, '{}')
        """, (asset_id, model, department, serial, warranty))
        conn.commit()
    finally:
        conn.close()

# ========================
#  AUTHENTIFIZIERUNG
# ========================
def authenticate(role: str) -> bool:
    """Prüft, ob der Benutzer für eine Rolle angemeldet ist. Falls nicht, zeigt das Passwortfeld."""
    auth_key = f"auth_{role}"
    if st.session_state.get(auth_key):
        return True

    def check_password():
        if hmac.compare_digest(st.session_state[f"pw_{role}"], PASSWORDS.get(role, "")):
            st.session_state[auth_key] = True
            del st.session_state[f"pw_{role}"]
        else:
            st.error("❌ Passwort falsch")

    st.warning(f"⚠️ {role.upper()}-Sperre aktiv.")
    st.text_input(f"Passwort für {role}", type="password", on_change=check_password, key=f"pw_{role}")
    return False

# ========================
#  UI HELFER
# ========================
def color_status(val: str) -> str:
    """Liefert CSS-Styling für den Status einer Anfrage."""
    if val == 'offen':
        return 'color: orange; font-weight: bold'
    if val == 'genehmigt':
        return 'color: green; font-weight: bold'
    if 'Einkauf' in val or 'Bestellung' in val:
        return 'color: #1E90FF; font-weight: bold'
    return 'color: red; font-weight: bold'

def get_garantie_status(garantie_str: str) -> str:
    """Berechnet den Garantiestatus (grün/gelb/rot) basierend auf dem aktuellen Datum."""
    if not garantie_str or garantie_str in ["None", "-", ""]:
        return "⚪ Unbekannt"
    try:
        garantie_date = datetime.strptime(f"01.{garantie_str}", "%d.%m.%Y")
        diff = (garantie_date - datetime.now()).days
        if diff < 0:
            return "🔴 Kritisch"
        if diff <= 180:
            return "🟡 Warnung"
        return "🟢 Gesund"
    except Exception:
        return "⚪ Unbekannt"

# ========================
#  UI TABS
# ========================
def user_tab() -> None:
    """Tab für normale Benutzer – Servicekatalog und Anfragen."""
    st.header("🛒 Service Katalog")

    with st.sidebar:
        # Logo anzeigen, falls vorhanden
        logo_path = "grafik.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.title("🐟 BlueMarlin")
        st.header("👤 Profil")
        user_name = st.text_input("Dein Name", "Max Mustermann")
        user_dept = st.selectbox("Abteilung", ["Vertrieb", "Grafik", "IT", "Buchhaltung", "Logistik"])

    request_type = st.radio("Was benötigst du?", ["Hardware", "Service"])

    if request_type == "Hardware":
        df_inv = load_inventory()
        available = df_inv[(df_inv['abteilung'].isin([user_dept, "Alle"])) & (df_inv['status'] == "Lager")]
        if available.empty:
            st.info("Aktuell keine Hardware im Lager verfügbar.")
        else:
            for _, row in available.iterrows():
                with st.container(border=True):
                    st.write(f"💻 **{row['typ']}** (ID: {row['id']})")
                    if st.button(f"Anfordern: {row['id']}", key=f"req_{row['id']}"):
                        add_request(user_name, user_dept, 'asset', row['id'])
                        st.toast("Hardware-Anfrage gesendet!")
                        st.rerun()
    else:  # Service
        services = load_services_for_department(user_dept)
        for _, s_row in services.iterrows():
            with st.container(border=True):
                st.write(f"🛠️ **{s_row['name']}**")
                st.caption(s_row['beschreibung'])
                st.write(f"⏱️ Dauer: {s_row['standard_dauer']}")
                if st.button(f"Service buchen: {s_row['id']}", key=f"svc_{s_row['id']}"):
                    add_request(user_name, user_dept, 'service', s_row['id'])
                    st.toast("Anfrage gesendet!")
                    st.rerun()

    st.divider()
    with st.expander("📋 Meine letzten Anfragen & Status einsehen"):
        history = load_user_requests(user_name)
        if not history.empty:
            st.table(history.style.map(color_status, subset=['status']))
        else:
            st.caption("Du hast noch keine Anfragen gestellt.")

def admin_tab() -> None:
    """Tab für Administratoren – CMDB, Anfragen verwalten, Export, Neuanlage."""
    if not authenticate("admin"):
        return

    st.header("🛠️ Management Konsole (CMDB)")
    df_admin = load_inventory()

    # Garantiestatus berechnen
    df_admin['Garantie_Check'] = df_admin['garantie_bis'].apply(get_garantie_status)
    crit_count = len(df_admin[df_admin['Garantie_Check'] == "🔴 Kritisch"])
    warn_count = len(df_admin[df_admin['Garantie_Check'] == "🟡 Warnung"])
    ok_count = len(df_admin[df_admin['Garantie_Check'] == "🟢 Gesund"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Abgelaufen", crit_count)
    m2.metric("Ablaufend (<6 Mon)", warn_count)
    m3.metric("Garantie OK", ok_count)

    # Filter
    st.write("🔍 **CMDB Schnell-Filter:**")
    f1, f2, f3, f4 = st.columns(4)
    if 'cmdb_filter' not in st.session_state:
        st.session_state['cmdb_filter'] = "Alle"
    if f1.button("🌐 Alle", use_container_width=True):
        st.session_state['cmdb_filter'] = "Alle"
    if f2.button("🔴 Kritisch", use_container_width=True):
        st.session_state['cmdb_filter'] = "🔴 Kritisch"
    if f3.button("🟡 Warnung", use_container_width=True):
        st.session_state['cmdb_filter'] = "🟡 Warnung"
    if f4.button("🟢 Gesund", use_container_width=True):
        st.session_state['cmdb_filter'] = "🟢 Gesund"

    current_filter = st.session_state['cmdb_filter']
    disp_df = df_admin if current_filter == "Alle" else df_admin[df_admin['Garantie_Check'] == current_filter]

    search = st.text_input("🔎 Globale Suche (ID, Modell, SN...)", "")
    if search:
        disp_df = disp_df[disp_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

    def style_rows(row):
        color = ""
        if row['Garantie_Check'] == "🔴 Kritisch":
            color = "background-color: rgba(255, 0, 0, 0.1)"
        elif row['Garantie_Check'] == "🟡 Warnung":
            color = "background-color: rgba(255, 255, 0, 0.1)"
        elif row['Garantie_Check'] == "⚪ Unbekannt":
            color = "background-color: rgba(128, 128, 128, 0.05)"
        return [color] * len(row)

    st.dataframe(disp_df.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)

    # Offene Anfragen
    st.divider()
    st.subheader("🔔 Offene Bestellanfragen")
    offene = load_requests_by_status('offen')
    if offene.empty:
        st.info("Keine neuen Anfragen vorhanden.")
    else:
        for _, row in offene.iterrows():
            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.write(f"👤 **{row['anfrager']}** ({row['abteilung']})")
                    st.write(f"Bedarf: `{row['referenz_id']}` | Typ: {row['typ']}")
                with col_action:
                    if st.button("✅ Genehmigen", key=f"app_{row['id']}", use_container_width=True):
                        approve_request(row['id'], row['anfrager'] if row['typ'] == 'asset' else None)
                        st.rerun()
                    if row['typ'] == 'asset':
                        if st.button("🛒 Nachkauf", key=f"proc_{row['id']}", use_container_width=True):
                            mark_for_procurement(row['id'])
                            st.rerun()

    # Export & Neuanlage
    st.divider()
    col_ex, col_new = st.columns(2)
    with col_ex:
        st.subheader("🚀 Daten-Export")
        if st.button("CSV Export (Smart)"):
            processed = [json.loads(x) if isinstance(x, str) and x.startswith('{') else {} for x in df_admin['details_json']]
            tech_cols = pd.json_normalize(processed)
            tech_cols.index = df_admin.index
            final_export = pd.concat([df_admin.drop(columns=['details_json']), tech_cols], axis=1)
            csv = final_export.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button("Download Starten", data=csv, file_name="IT_Inventar_Export.csv")

    with col_new:
        st.subheader("➕ Asset registrieren")
        with st.expander("Formular öffnen"):
            with st.form("new_asset"):
                f1, f2, f3 = st.columns(3)
                nid = f1.text_input("Asset ID")
                ntyp = f2.text_input("Modell")
                nabt = f3.selectbox("Abteilung", ["IT", "Grafik", "Vertrieb", "Buchhaltung", "Logistik"])
                n_sn = st.text_input("Seriennummer")
                n_gar = st.text_input("Garantie (MM.YYYY)")
                if st.form_submit_button("Speichern"):
                    add_asset(nid, ntyp, nabt, n_sn, n_gar)
                    st.rerun()

    st.divider()
    with st.expander("⚠️ System-Wartung (Gefahrenzone)"):
        st.write("Hier kannst du alle Testdaten zurücksetzen, um die Demo von vorne zu starten.")
        if st.button("🗑️ Alle Anfragen & Bestellungen löschen"):
            clear_requests_and_reset_inventory()
            st.warning("Datenbank wurde bereinigt!")
            st.rerun()

    # Finanz-Dashboard
    st.divider()
    st.subheader("📊 Ausgaben nach Abteilung")
    total_spent, by_dept = load_budget_stats()
    if not by_dept.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.bar_chart(data=by_dept.set_index('abteilung'), y='total', color="#1E90FF")
        with c2:
            st.write("**Budget-Details:**")
            for _, row in by_dept.iterrows():
                st.write(f"🔹 {row['abteilung']}: {row['total']:,.2f} €")
    else:
        st.info("Noch keine Bestelldaten für das Dashboard vorhanden.")

def tech_tab() -> None:
    """Tab für Techniker – Detaillierte Geräteinformationen."""
    if not authenticate("tech"):
        return

    st.header("🔍 Technisches Dossier")
    df_tech = load_inventory()
    target = st.selectbox("Asset für Details wählen", df_tech['id'].tolist())
    if target:
        item = df_tech[df_tech['id'] == target].iloc[0]
        st.subheader(f"Konfiguration: {item['typ']}")
        col_spec, col_raw = st.columns(2)
        with col_spec:
            try:
                details = json.loads(item['details_json'])
                for k, v in details.items():
                    st.info(f"**{k}**: {v}")
            except Exception:
                st.write("Keine technischen Details hinterlegt.")
        with col_raw:
            st.caption("JSON Rohdaten")
            st.code(item['details_json'], language="json")

def procurement_tab() -> None:
    """Tab für Einkäufer – Bestellungen verwalten."""
    if not authenticate("procure"):
        return

    st.header("🛒 Beschaffungs-Management")

    # Spalte 'preis' sicherstellen (Migration)
    conn = get_connection()
    try:
        conn.execute("ALTER TABLE requests ADD COLUMN preis REAL")
    except sqlite3.OperationalError:
        pass  # Spalte existiert bereits
    finally:
        conn.close()

    total_spent, _ = load_budget_stats()
    st.metric("Gesamtbestellwert (laufend)", f"{total_spent:,.2f} €")
    st.divider()

    procure_req = load_requests_by_status('Einkauf prüfen')
    if procure_req.empty:
        st.info("Keine offenen Beschaffungsvorgänge.")
    else:
        for _, row in procure_req.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"📢 **Bedarf:** {row['referenz_id']}")
                    st.caption(f"Anfrager: {row['anfrager']} ({row['abteilung']})")
                with col2:
                    # Preis vorschlagen
                    suggested = 49.0  # Fallback
                    for key, price in PRICE_REFERENCE.items():
                        if key.lower() in row['referenz_id'].lower():
                            suggested = price
                            break
                    price = st.number_input(f"Preis für ID {row['id']} (€)",
                                            value=float(suggested), step=10.0, key=f"price_{row['id']}")
                with col3:
                    st.write("")
                    if st.button("📦 Bestellen", key=f"buy_{row['id']}", use_container_width=True):
                        order_item(row['id'], price)
                        st.success(f"Bestellt für {price} €")
                        st.rerun()

    # Historie der Bestellungen
    st.divider()
    with st.expander("📜 Letzte abgeschlossene Bestellungen"):
        conn = get_connection()
        try:
            completed_df = pd.read_sql("""
                SELECT erstellt_am as 'Datum', anfrager as 'Besteller',
                       referenz_id as 'Asset/Service', preis as 'Preis (€)',
                       kommentar as 'Info'
                FROM requests
                WHERE status = 'In Bestellung'
                ORDER BY id DESC LIMIT 10
            """, conn)
            if not completed_df.empty:
                st.dataframe(completed_df, use_container_width=True, hide_index=True)
            else:
                st.caption("Noch keine Bestellungen abgeschlossen.")
        finally:
            conn.close()

# ========================
#  HAUPTPROGRAMM
# ========================
def main():
    try:
        main()
    except Exception as e:
        st.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        st.stop()
def main() -> None:
    """Hauptfunktion der Streamlit-App."""
    st.set_page_config(page_title="BlueMarlin - IT Service Hub", layout="wide")
    init_database()

    st.title("🛡️ BlueMarlin-IT-Profis – Service Hub")
    tab_user, tab_admin, tab_tech, tab_procure = st.tabs(["🛒 Service Katalog", "⚙️ IT-Administration", "🛠️ Deep Tech", "🛒 Beschaffungs-Management"])

    with tab_user:
        user_tab()
    with tab_admin:
        admin_tab()
    with tab_tech:
        tech_tab()
    with tab_procure:
        procurement_tab()

    with st.sidebar:
        st.divider()
        with st.expander("🔑 Demo-Zugänge"):
            st.code("Admin: admin123\nTech: tech123\nEinkauf: procure123")

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
import sqlite3
import hmac
import json
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="BlueMarlin - IT Service Hub", layout="wide")

# --- 1. DATENBANK LOGIK ---
DB_FILE = "it_inventory_final.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Inventar-Tabelle (9 Spalten)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id TEXT PRIMARY KEY, typ TEXT, abteilung TEXT, status TEXT,
                    besitzer TEXT, last_update TEXT, seriennummer TEXT,
                    garantie_bis TEXT, details_json TEXT 
                )''')
    # Service-Tabelle
    c.execute('''CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY, name TEXT, beschreibung TEXT,
                    zielgruppe TEXT, status TEXT, standard_dauer TEXT
                )''')
    # Anfrage-Tabelle
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, anfrager TEXT,
                    abteilung TEXT, typ TEXT, referenz_id TEXT, status TEXT,
                    erstellt_am TEXT, letzte_aenderung TEXT, kommentar TEXT, preis REAL
                )''')
    conn.commit()
    conn.close()

def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM inventory", conn)
    conn.close()
    return df

def init_sample_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
        sample_services = [
            # --- ALLGEMEINE SERVICES (Alle) ---
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

            # --- IT SPEZIFISCH ---
            ("SVC-011", "Datenrettung", "Wiederherstellung verlorener Daten", "IT", "aktiv", "5 Tage"),
            ("SVC-012", "Hardware-Upgrade", "Aufrüstung bestehender Hardware", "IT", "aktiv", "7 Tage"),
            ("SVC-013", "Netzwerk-Setup", "Einrichtung von Netzwerken", "IT", "aktiv", "3 Tage"),
            ("SVC-014", "Cloud-Migration", "Unterstützung bei Cloud-Umzug", "IT", "aktiv", "10 Tage"),

            # --- VERTRIEB ---
            ("SVC-015", "Notebook-Setup", "Grundkonfiguration", "Vertrieb", "aktiv", "3 Tage"),

            # --- LOGISTIK ---
            ("SVC-016", "Lager-WLAN-Check", "Signalstärkenmessung für Scanner", "Logistik", "aktiv", "1 Tag"),
            ("SVC-017", "Scanner-Konfiguration", "Anbindung an das ERP-System", "Logistik", "aktiv", "2 Std"),

            # --- BUCHHALTUNG ---
            ("SVC-018", "DATEV-Support", "Update & Schnittstellenprüfung", "Buchhaltung", "aktiv", "1 Tag"),
            ("SVC-019", "Archiv-Migration", "Digitale Belegarchivierung Setup", "Buchhaltung", "aktiv", "5 Tage")
        ]
        c.executemany("INSERT INTO services VALUES (?,?,?,?,?,?)", sample_services)
        conn.commit()
    conn.close()

def init_inventory_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        # Technische Details (Dossiers)
        tech_srv = '{"IP": "192.168.10.15", "OS": "Ubuntu 22.04", "CPU": "2x Xeon", "RAM": "128GB"}'
        tech_tablet = '{"IP": "DHCP", "Schutzklasse": "IP65", "Display": "Glove-Touch", "Akku": "12h"}'
        tech_panel = '{"OS": "Win10 IoT", "Montage": "VESA 100", "Kühlung": "Passiv", "Anschlüsse": "RS232"}'
        
        sample_assets = [
            # --- IT ABTEILUNG ---
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

            # --- GRAFIK ABTEILUNG ---
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

            # --- VERTRIEB ---
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

            # --- LOGISTIK ---
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

            # --- BUCHHALTUNG ---
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
        c.executemany("INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?,?)", sample_assets)
        conn.commit()
    conn.close()

# --- 2. SECURITY (ROLLEN-TRENNUNG) ---
def check_password(role="admin"):
    auth_key = f"auth_{role}"
    if st.session_state.get(auth_key):
        return True

    def password_entered():
        passwords = {"admin": "admin123", "tech": "tech123", "procure": "procure123"}
        if hmac.compare_digest(st.session_state[f"pw_{role}"], passwords[role]):
            st.session_state[auth_key] = True
            del st.session_state[f"pw_{role}"]
        else:
            st.error("❌ Passwort falsch")

    st.warning(f"⚠️ {role.upper()}-Sperre aktiv.")
    st.text_input(f"Passwort für {role}", type="password", on_change=password_entered, key=f"pw_{role}")
    return False

# --- 3. APP START ---
init_db()
init_sample_data()
init_inventory_data()

st.title("🛡️ BlueMarlin-IT-Profis – Service Hub")
tab_user, tab_admin, tab_tech, tab_procure = st.tabs(["🛒 Service Katalog", "⚙️ IT-Administration", "🛠️ Deep Tech", "🛒 Beschaffungs-Management"])


def color_status(val):
    if val == 'offen': return 'color: orange; font-weight: bold'
    if val == 'genehmigt': return 'color: green; font-weight: bold'
    if 'Einkauf' in val or 'Bestellung' in val: return 'color: #1E90FF; font-weight: bold' # Ein schönes Blau
    return 'color: red; font-weight: bold'

# --- USER TAB ---
with tab_user:
    with st.sidebar:
        import os
        
        # Sicherstellen, dass wir im richtigen Verzeichnis suchen
        img_name = "grafik.png"
        # Wir prüfen, ob die Datei im aktuellen Arbeitsverzeichnis existiert
        if os.path.exists(img_name):
            st.image(img_name, use_container_width=True)
        else:
            # Falls David die Datei anders benannt hat (z.B. .png oder Großbuchstaben)
            st.error(f"⚠️ Datei '{img_name}' nicht gefunden.")
            st.info(f"Aktueller Ordner: {os.getcwd()}")
            st.title("🐟 BlueMarlin")
            
        st.header("👤 Profil")
        u_name = st.text_input("Dein Name", "Max Mustermann")
        # Abteilungen um Logistik und Buchhaltung erweitert
        u_dept = st.selectbox("Abteilung", ["Vertrieb", "Grafik", "IT", "Buchhaltung", "Logistik"])
    
    anfrage_typ = st.radio("Was benötigst du?", ["Hardware", "Service"])
    df_user = load_data()
    
    if anfrage_typ == "Hardware":
        verfügbar = df_user[(df_user['abteilung'].isin([u_dept, "Alle"])) & (df_user['status'] == "Lager")]
        if verfügbar.empty:
            st.info("Aktuell keine Hardware im Lager verfügbar.")
        else:
            for _, row in verfügbar.iterrows():
                with st.container(border=True):
                    st.write(f"💻 **{row['typ']}** (ID: {row['id']})")
                    if st.button(f"Anfordern: {row['id']}", key=f"req_{row['id']}"):
                        conn = get_connection()
                        conn.execute("INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am) VALUES (?,?,'asset',?,'offen',?)",
                                     (u_name, u_dept, row['id'], datetime.now().strftime("%d.%m.%Y %H:%M")))
                        conn.commit(); conn.close(); st.toast("Hardware-Anfrage gesendet!"); st.rerun()
    else:
        conn = get_connection()
        services_df = pd.read_sql("SELECT * FROM services WHERE zielgruppe IN (?, 'Alle')", conn, params=(u_dept,))
        conn.close()
        for _, s_row in services_df.iterrows():
            with st.container(border=True):
                st.write(f"🛠️ **{s_row['name']}**")
                st.caption(s_row['beschreibung'])
                st.write(f"⏱️ Dauer: {s_row['standard_dauer']}")
                if st.button(f"Service buchen: {s_row['id']}", key=f"svc_{s_row['id']}"):
                    conn = get_connection()
                    conn.execute("INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am) VALUES (?,?,'service',?,'offen',?)",
                                 (u_name, u_dept, s_row['id'], datetime.now().strftime("%d.%m.%Y %H:%M")))
                    conn.commit(); conn.close(); st.toast("Anfrage gesendet!"); st.rerun()

    st.divider()
    with st.expander("📋 Meine letzten Anfragen & Status einsehen"):
        conn = get_connection()
        history_df = pd.read_sql("""
            SELECT typ, referenz_id, status, erstellt_am 
            FROM requests 
            WHERE anfrager = ? 
            ORDER BY erstellt_am DESC LIMIT 5
        """, conn, params=(u_name,))
        conn.close()

        if not history_df.empty:
            st.table(history_df.style.map(color_status, subset=['status']))
        else:
            st.caption("Du hast noch keine Anfragen gestellt.")

# --- ADMIN TAB ---
with tab_admin:
    if check_password(role="admin"):
        st.header("🛠️ Management Konsole (CMDB)")
        df_admin = load_data()
        
        # --- 1. AMPEL-LOGIK & DASHBOARD ---
        today = datetime.now()
        
        def get_check_status(g_str):
            if not g_str or g_str in ["None", "-", ""]: return "⚪ Unbekannt"
            try:
                g_date = datetime.strptime(f"01.{g_str}", "%d.%m.%Y")
                diff = (g_date - today).days
                if diff < 0: return "🔴 Kritisch"
                elif diff <= 180: return "🟡 Warnung"
                else: return "🟢 Gesund"
            except: return "⚪ Unbekannt"

        # Status-Spalte für die Tabelle berechnen
        df_admin['Garantie_Check'] = df_admin['garantie_bis'].apply(get_check_status)
        
        crit_count = len(df_admin[df_admin['Garantie_Check'] == "🔴 Kritisch"])
        warn_count = len(df_admin[df_admin['Garantie_Check'] == "🟡 Warnung"])
        ok_count = len(df_admin[df_admin['Garantie_Check'] == "🟢 Gesund"])

        # Metriken Anzeigen
        m1, m2, m3 = st.columns(3)
        m1.metric("Abgelaufen", crit_count)
        m2.metric("Ablaufend (<6 Mon)", warn_count)
        m3.metric("Garantie OK", ok_count)

        # --- 2. FILTER-SYSTEM ---
        st.write("🔍 **CMDB Schnell-Filter:**")
        f1, f2, f3, f4 = st.columns(4)
        
        # Wir nutzen session_state, um den Filter-Status zu halten
        if 'cmdb_filter' not in st.session_state:
            st.session_state['cmdb_filter'] = "Alle"

        if f1.button("🌐 Alle", use_container_width=True): st.session_state['cmdb_filter'] = "Alle"
        if f2.button("🔴 Kritisch", use_container_width=True): st.session_state['cmdb_filter'] = "🔴 Kritisch"
        if f3.button("🟡 Warnung", use_container_width=True): st.session_state['cmdb_filter'] = "🟡 Warnung"
        if f4.button("🟢 Gesund", use_container_width=True): st.session_state['cmdb_filter'] = "🟢 Gesund"

        # Daten basierend auf Filter und Suche vorbereiten
        current_filter = st.session_state['cmdb_filter']
        disp_df = df_admin if current_filter == "Alle" else df_admin[df_admin['Garantie_Check'] == current_filter]
        
        search = st.text_input("🔎 Globale Suche (ID, Modell, SN...)", "")
        if search:
            disp_df = disp_df[disp_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

        # Tabelle mit farblicher Markierung anzeigen
        def style_rows(row):
            color = ""
            if row['Garantie_Check'] == "🔴 Kritisch": color = "background-color: rgba(255, 0, 0, 0.1)"
            elif row['Garantie_Check'] == "🟡 Warnung": color = "background-color: rgba(255, 255, 0, 0.1)"
            elif row['Garantie_Check'] == "⚪ Unbekannt":
               color = "background-color: rgba(128, 128, 128, 0.05)" # Ganz dezentes Grau
            return [color] * len(row)

        st.dataframe(disp_df.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)

        # --- 3. OFFENE ANFRAGEN ---
        st.divider()
        st.subheader("🔔 Offene Bestellanfragen")
        conn = get_connection()
        offene_req = pd.read_sql("SELECT * FROM requests WHERE status = 'offen'", conn)
        conn.close()
        
        if offene_req.empty:
            st.info("Keine neuen Anfragen vorhanden.")
        else:
            for _, r_row in offene_req.iterrows():
                with st.container(border=True):
                    col_info, col_action = st.columns([3, 1])
                    with col_info:
                        st.write(f"👤 **{r_row['anfrager']}** ({r_row['abteilung']})")
                        st.write(f"Bedarf: `{r_row['referenz_id']}` | Typ: {r_row['typ']}")
                    
                    with col_action:
                        if st.button("✅ Genehmigen", key=f"app_{r_row['id']}", use_container_width=True):
                            c = get_connection()
                            c.execute("UPDATE requests SET status = 'genehmigt' WHERE id = ?", (r_row['id'],))
                            if r_row['typ'] == 'asset':
                                c.execute("""UPDATE inventory SET status = 'In Benutzung', besitzer = ?, last_update = ? 
                                          WHERE id = ?""", (r_row['anfrager'], datetime.now().strftime("%d.%m.%Y"), r_row['referenz_id']))
                            c.commit(); c.close(); st.rerun()
                        
                        if r_row['typ'] == 'asset':
                            if st.button("🛒 Nachkauf", key=f"proc_{r_row['id']}", use_container_width=True):
                                c = get_connection()
                                c.execute("UPDATE requests SET status = 'Einkauf prüfen' WHERE id = ?", (r_row['id'],))
                                c.commit(); c.close(); st.rerun()

        # --- 4. EXPORT & NEUANLAGE ---
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
                        conn = get_connection()
                        conn.execute("INSERT INTO inventory VALUES (?,?,?, 'Lager', '-', '-', ?, ?, '{}')", (nid, ntyp, nabt, n_sn, n_gar))
                        conn.commit(); conn.close(); st.rerun()
        st.divider()
        with st.expander("⚠️ System-Wartung (Gefahrenzone)"):
            st.write("Hier kannst du alle Testdaten zurücksetzen, um die Demo von vorne zu starten.")
            if st.button("🗑️ Alle Anfragen & Bestellungen löschen"):
                conn = get_connection()
                conn.execute("DELETE FROM requests")
                # Inventar-Status zurücksetzen (optional)
                conn.execute("UPDATE inventory SET status = 'Lager', besitzer = '-', last_update = '-'")
                conn.commit()
                conn.close()
                st.warning("Datenbank wurde bereinigt!")
                st.rerun()                

        # --- 5. FINANZ-DASHBOARD ---
        st.divider()
        st.subheader("📊 Ausgaben nach Abteilung")
        conn = get_connection()
        # Ersetze die SQL-Abfrage im Finanz-Dashboard (Admin Tab Punkt 5) durch diese:
        stats_df = pd.read_sql("""
            SELECT abteilung, SUM(preis) as total 
            FROM requests 
            WHERE status = 'In Bestellung' 
            GROUP BY abteilung
        """, conn)
        conn.close()

        if not stats_df.empty:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.bar_chart(data=stats_df.set_index('abteilung'), y='total', color="#1E90FF")
            with c2:
                st.write("**Budget-Details:**")
                for _, row in stats_df.iterrows():
                    st.write(f"🔹 {row['abteilung']}: {row['total']:,.2f} €")
        else:
            st.info("Noch keine Bestelldaten für das Dashboard vorhanden.")       

# --- TECH TAB (Optimiert) ---
with tab_tech:
    if check_password(role="tech"):
        st.header("🔍 Technisches Dossier")
        df_tech = load_data()
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
                except:
                    st.write("Keine technischen Details hinterlegt.")
            with col_raw:
                st.caption("JSON Rohdaten")
                st.code(item['details_json'], language="json")

# --- NEUER TAB: EINKAUF (Finale Version mit Historie & Fallback) ---
with tab_procure:
    if check_password(role="procure"): 
        st.header("🛒 Beschaffungs-Management")
        
        preise_ref = {
            # ... (deine Preisliste bleibt gleich)
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

        conn = get_connection()
        # Migration: Spalte 'preis' sicherstellen
        try:
            conn.execute("ALTER TABLE requests ADD COLUMN preis REAL")
        except:
            pass

        procure_req = pd.read_sql("SELECT * FROM requests WHERE status = 'Einkauf prüfen'", conn)
        
        # Statistik (Live-Budget)
        total_spent = pd.read_sql("SELECT SUM(preis) FROM requests WHERE status = 'In Bestellung'", conn).iloc[0,0] or 0.0
        st.metric("Gesamtbestellwert (laufend)", f"{total_spent:,.2f} €")
        
        st.divider()

        if procure_req.empty:
            st.info("Keine offenen Beschaffungsvorgänge.")
        else:
            for _, p_row in procure_req.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"📢 **Bedarf:** {p_row['referenz_id']}")
                        st.caption(f"Anfrager: {p_row['anfrager']} ({p_row['abteilung']})")
                    
                    with col2:
                        # Logik für den Preis-Vorschlag
                        vorschlag = 49.0  # Standard-Fallback (z.B. für kleine Lizenzen)
                        for key in preise_ref:
                            if key.lower() in p_row['referenz_id'].lower():
                                vorschlag = preise_ref[key]
                                break 
                        
                        einkaufspreis = st.number_input(f"Preis für ID {p_row['id']} (€)", 
                                                       value=float(vorschlag), step=10.0, key=f"price_{p_row['id']}")

                    with col3:
                        st.write("") # Spacer
                        if st.button("📦 Bestellen", key=f"buy_{p_row['id']}", use_container_width=True):
                            c = get_connection()
                            c.execute("""UPDATE requests 
                                       SET status = 'In Bestellung', 
                                           preis = ?, 
                                           kommentar = 'Bestellt am ' || ? 
                                       WHERE id = ?""", 
                                     (einkaufspreis, datetime.now().strftime("%d.%m.%Y"), p_row['id']))
                            c.commit()
                            c.close()
                            st.success(f"Bestellt für {einkaufspreis} €")
                            st.rerun()
        conn.close()
        
        # --- HISTORIE DER BESTELLUNGEN (Sauber formatiert) ---
        st.divider()
        with st.expander("📜 Letzte abgeschlossene Bestellungen"):
            conn = get_connection()
            completed_df = pd.read_sql("""
                SELECT erstellt_am as 'Datum', anfrager as 'Besteller', 
                       referenz_id as 'Asset/Service', preis as 'Preis (€)', 
                       kommentar as 'Info' 
                FROM requests 
                WHERE status = 'In Bestellung' 
                ORDER BY id DESC LIMIT 10
            """, conn)
            conn.close()
            
            if not completed_df.empty:
                st.dataframe(completed_df, use_container_width=True, hide_index=True)
            else:
                st.caption("Noch keine Bestellungen abgeschlossen.")
        
        #--- NEU: HISTORIE DER BESTELLUNGEN ---
        st.divider()
        with st.expander("📜 Letzte abgeschlossene Bestellungen"):
            conn = get_connection()
            completed_df = pd.read_sql("""
                SELECT erstellt_am, anfrager, referenz_id, preis, kommentar 
                FROM requests 
                WHERE status = 'In Bestellung' 
                ORDER BY id DESC LIMIT 10
            """, conn)
            conn.close()
            
            if not completed_df.empty:
                st.dataframe(completed_df, use_container_width=True, hide_index=True)
            else:
                st.caption("Noch keine Bestellungen abgeschlossen.")

# Hilfreiche Info für Tester in der Sidebar
with st.sidebar:
    st.divider()
    with st.expander("🔑 Demo-Zugänge"):
        st.code("Admin: admin123\nTech: tech123\nEinkauf: procure123")                        



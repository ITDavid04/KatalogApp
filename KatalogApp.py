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
            ("SVC-001", "Adobe Creative Cloud", "Installation & Lizenz", "Alle", "aktiv", "2 Tage"),
            ("SVC-002", "VPN-Zugang", "Einrichtung Homeoffice", "Alle", "aktiv", "1 Tag"),
            ("SVC-003", "Notebook-Setup", "Grundkonfiguration", "Vertrieb", "aktiv", "3 Tage"),
            ("SVC-004", "Software-Lizenz", "Verwaltung von Softwarelizenzen", "Alle", "aktiv", "1 Tag"),
            ("SVC-005", "Datenrettung", "Wiederherstellung verlorener Daten", "IT", "aktiv", "5 Tage"),
            ("SVC-006", "Hardware-Upgrade", "Aufrüstung bestehender Hardware", "IT", "aktiv", "7 Tage"),
            ("SVC-007", "IT-Support", "Allgemeine IT-Unterstützung", "Alle", "aktiv", "1 Tag"),
            ("SVC-008", "Schulungen", "IT-Schulungen für Mitarbeiter", "Alle", "aktiv", "Variabel"),
            ("SVC-009", "Netzwerk-Setup", "Einrichtung von Netzwerken", "IT", "aktiv", "3 Tage"),
            ("SVC-010", "Sicherheitsüberprüfung", "IT-Sicherheitsaudit", "Alle", "aktiv", "4 Tage"),
            ("SVC-011", "Cloud-Migration", "Unterstützung bei Cloud-Umzug", "IT", "aktiv", "10 Tage"),
            ("SVC-012", "Geräteentsorgung", "Sichere Entsorgung von Altgeräten", "Alle", "aktiv", "2 Tage"),
            ("SVC-013", "Software-Update", "Regelmäßige Softwareaktualisierungen", "Alle", "aktiv", "1 Tag"),
            ("SVC-014", "Passwort-Reset", "Zurücksetzen von Passwörtern", "Alle", "aktiv", "1 Tag"),
            ("SVC-015", "IT-Beratung", "Beratung zu IT-Anschaffungen", "Alle", "aktiv", "Variabel"),
            # --- ERGÄNZUNGEN LOGISTIK & BUCHHALTUNG ---
            ("SVC-016", "Lager-WLAN-Check", "Signalstärkenmessung für Scanner", "Logistik", "aktiv", "1 Tag"),
            ("SVC-017", "Scanner-Konfiguration", "Anbindung an das ERP-System", "Logistik", "aktiv", "2 Std"),
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
            ("HW-IT-001", "ThinkPad X1 Carbon", "IT", "Lager", "-", "-", "SN-9921-X1", "01.2027", '{"RAM": "16GB"}'),
            ("HW-IT-002", "Dell PowerEdge R740", "IT", "In Benutzung", "Admin", "25.03.2026", "SRV-DELL-01", "12.2028", tech_srv),
            ("HW-GR-001", "Mac Studio (M2)", "Grafik", "Lager", "-", "-", "APPLE-M2-088", "06.2027", '{"GPU": "30 Core"}'),
            ("HW-VT-001", "iPhone 15 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-334455", "10.2026", '{"MDM": "Active"}'),
            ("HW-IT-003", "HP EliteBook 840", "IT", "In Benutzung", "Mitarbeiter A", "10.01.2024", "SN-HP-840-55", "03.2025", '{"RAM": "8GB"}'),
            ("HW-IT-004", "Lenovo ThinkStation P360", "IT", "Lager", "-", "-", "SN-LEN-P360-77", "11.2026", '{"GPU": "NVIDIA RTX A2000"}'),
            ("HW-GR-002", "Wacom Cintiq Pro 24", "Grafik", "In Benutzung", "Mitarbeiter B", "15.02.2024", "SN-WACOM-CINTIQ-24", "02.2025", '{"Druckstufen": "8192"}'),
            ("HW-VT-002", "Samsung Galaxy S23", "Vertrieb", "In Benutzung", "Mitarbeiter C", "20.03.2024", "IMEI-556677", "09.2026", '{"MDM": "Active"}'),
            ("HW-IT-005", "Apple MacBook Pro 16", "IT", "Lager", "-", "-", "SN-APPLE-MBP16-99", "08.2027", '{"CPU": "M1 Pro"}'),
            ("HW-IT-006", "Asus ROG Zephyrus G14", "IT", "In Benutzung", "Mitarbeiter D", "05.04.2024", "SN-ASUS-G14-88", "04.2025", '{"GPU": "NVIDIA RTX 3060"}'),
            ("HW-GR-003", "Eizo ColorEdge CG319X", "Grafik", "Lager", "-", "-", "SN-EIZO-CG319X-66", "09.2026", '{"Auflösung": "4096x2160"}'),
            ("HW-VT-003", "Google Pixel 7 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-778899", "12.2026", '{"MDM": "Active"}'),
            ("HW-IT-007", "Microsoft Surface Laptop 4", "IT", "In Benutzung", "Mitarbeiter E", "12.04.2024", "SN-MS-SURFACE-44", "05.2025", '{"RAM": "16GB"}'),
            ("HW-IT-008", "Dell XPS 15", "IT", "Lager", "-", "-", "SN-DELL-XPS15-33", "07.2027", '{"CPU": "Intel i7"}'),
            ("HW-GR-004", "BenQ PD3220U", "Grafik", "In Benutzung", "Mitarbeiter F", "18.02.2024", "SN-BENQ-PD3220U-22", "01.2025", '{"Farbgenauigkeit": "99% AdobeRGB"}'),
            ("HW-VT-004", "OnePlus 11", "Vertrieb", "In Benutzung", "Mitarbeiter G", "25.03.2024", "IMEI-990011", "11.2026", '{"MDM": "Active"}'),
            # --- NEUE ASSETS FÜR LOGISTIK ---
            ("HW-LOG-001", "Zebra L10 Rugged Tablet", "Logistik", "Lager", "-", "-", "SN-ZEB-990", "12.2026", tech_tablet),
            ("HW-LOG-002", "Advantech Panel-PC 15\"", "Logistik", "Lager", "-", "-", "SN-ADV-P15", "05.2027", tech_panel),
            ("HW-LOG-003", "Datalogic Handscanner", "Logistik", "In Benutzung", "Lagerhalle Süd", "12.03.2026", "SN-DL-SCAN-01", "08.2026", '{"Typ": "2D-Imager"}'),
            # --- NEUE ASSETS FÜR BUCHHALTUNG ---
            ("HW-ACC-001", "Fujitsu Belegscanner ix1600", "Buchhaltung", "Lager", "-", "-", "SN-FUJ-SCAN-01", "03.2027", '{"Speed": "40ppm"}'),
            ("HW-ACC-002", "Dell UltraSharp Dual-Set", "Buchhaltung", "In Benutzung", "Finanzabteilung", "05.01.2026", "SN-DELL-DUAL", "11.2026", '{"Zoll": "2x 27"}')
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
        st.header("🛠️ Management Konsole")
        df_admin = load_data()
        
        # 1. AMPEL-ANZEIGE (Dashboard Status)
        today = datetime.now()
        crit, warn = 0, 0
        for _, row in df_admin.iterrows():
            g_str = row['garantie_bis']
            if g_str and g_str not in ["None", "-", ""]:
                try:
                    g_date = datetime.strptime(f"01.{g_str}", "%d.%m.%Y")
                    diff = (g_date - today).days
                    if diff < 0: crit += 1
                    elif diff <= 180: warn += 1
                except: continue
        
        a1, a2, a3 = st.columns(3)
        a1.error(f"🔴 Kritisch: {crit}")
        a2.warning(f"🟡 Warning: {warn}")
        a3.success(f"🟢 Gesund: {len(df_admin)-crit-warn}")

        # 2. BESTÄTIGUNGS-LOGIK (Offene Aufgaben)
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
                        st.write(f"👤 **{r_row['anfrager']}** bittet um **{r_row['referenz_id']}**")
                        st.caption(f"Abteilung: {r_row['abteilung']} | Typ: {r_row['typ']} | Am: {r_row['erstellt_am']}")
                    
                    with col_action:
                        # Button A: Direkt aus dem Lager zuteilen
                        if st.button("✅ Genehmigen", key=f"app_{r_row['id']}", use_container_width=True):
                            c = get_connection()
                            c.execute("UPDATE requests SET status = 'genehmigt' WHERE id = ?", (r_row['id'],))
                            if r_row['typ'] == 'asset':
                                c.execute("""UPDATE inventory SET status = 'In Benutzung', besitzer = ?, last_update = ? 
                                          WHERE id = ?""", (r_row['anfrager'], datetime.now().strftime("%d.%m.%Y"), r_row['referenz_id']))
                            c.commit()
                            c.close()
                            st.success(f"Zuweisung für {r_row['anfrager']} erfolgt!")
                            st.rerun()
                        
                        # Button B: An den Einkauf weiterleiten
                        if r_row['typ'] == 'asset':
                            if st.button("🛒 Nachkauf", key=f"proc_{r_row['id']}", use_container_width=True):
                                c = get_connection()
                                c.execute("UPDATE requests SET status = 'Einkauf prüfen' WHERE id = ?", (r_row['id'],))
                                c.commit()
                                c.close()
                                st.info("An Einkauf delegiert!")
                                st.rerun()

        # 3. INVENTAR-SUCHE & TABELLE
        st.divider()
        search = st.text_input("🔍 Asset Suche", "")
        disp_df = df_admin[df_admin.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df_admin
        st.dataframe(disp_df, use_container_width=True)
        
        # 4. EXPORT & NEUANLAGE
        if not df_admin.empty:
            if st.button("🚀 Excel-Export vorbereiten"):
                processed = [json.loads(x) if isinstance(x, str) and x.startswith('{') else {} for x in df_admin['details_json']]
                tech_cols = pd.json_normalize(processed)
                tech_cols.index = df_admin.index
                final_export = pd.concat([df_admin.drop(columns=['details_json']), tech_cols], axis=1)
                csv = final_export.to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button("Download CSV (Smart)", data=csv, file_name="IT_Inventar_Export.csv")

        with st.expander("➕ Neues Asset registrieren"):
            with st.form("new_asset"):
                f1, f2, f3 = st.columns(3)
                nid = f1.text_input("ID")
                ntyp = f2.text_input("Modell")
                nabt = f3.selectbox("Abteilung", ["Alle", "IT", "Grafik", "Vertrieb"])
                n_sn = st.text_input("Seriennummer")
                n_gar = st.text_input("Garantie bis", placeholder="MM.YYYY (z.B. 12.2026)")
                if st.form_submit_button("Speichern"):
                    conn = get_connection()
                    conn.execute("INSERT INTO inventory VALUES (?,?,?, 'Lager', '-', '-', ?, ?, '{}')", (nid, ntyp, nabt, n_sn, n_gar))
                    conn.commit()
                    conn.close()
                    st.rerun()
                    
        # --- 5. FINANZ-DASHBOARD (Bonus) ---
        st.divider()
        st.subheader("📊 Ausgaben nach Abteilung")
        
        conn = get_connection()
        # Wir holen uns alle genehmigten oder bestellten Anfragen mit Preisen
        stats_df = pd.read_sql("""
            SELECT abteilung, SUM(preis) as total 
            FROM requests 
            WHERE preis > 0 
            GROUP BY abteilung
        """, conn)
        conn.close()

        if not stats_df.empty:
            c1, c2 = st.columns([2, 1])
            with c1:
                # Ein einfaches, schickes Balkendiagramm
                st.bar_chart(data=stats_df.set_index('abteilung'), y='total', color="#1E90FF")
            with c2:
                # Die nackten Zahlen daneben
                st.write("**Details:**")
                for _, row in stats_df.iterrows():
                    st.write(f"🔹 {row['abteilung']}: {row['total']:,.2f} €")
        else:
            st.info("Noch keine Bestelldaten für eine statistische Auswertung vorhanden.")            

# --- TECH TAB ---
with tab_tech:
    if check_password(role="tech"):
        st.header("🔍 Technisches Dossier")
        df_tech = load_data()
        target = st.selectbox("Asset für Details wählen", df_tech['id'].tolist())
        if target:
            item = df_tech[df_tech['id'] == target].iloc[0]
            st.subheader(f"Konfiguration: {item['typ']}")
            try:
                details = json.loads(item['details_json'])
                for k, v in details.items():
                    st.info(f"**{k}**: {v}")
            except:
                st.write("Keine technischen Details hinterlegt.")

# --- NEUER TAB: EINKAUF ---
with tab_procure:
    if check_password(role="procure"): 
        st.header("🛒 Beschaffungs-Management")
        
        # Kleine Preis-Referenz (Beispiel-Assets)
        preise_ref = {
            "Zebra": 2400.0,      # Logistik Industrie-Tablet
            "Advantech": 1850.0,  # Logistik Panel-PC
            "Datalogic": 350.0,   # Handscanner
            "Fujitsu": 450.0,     # Belegscanner Buchhaltung
            "ThinkPad": 1450.0,
            "iPhone": 1100.0,
            "MacBook Pro": 2100.0,
            "Dell": 1600.0,
            "HP": 1200.0,
            "Wacom": 2200.0,
            "Eizo": 5000.0,
            "BenQ": 1300.0,
            "Surface": 1700.0,
            "Samsung": 900.0,
            "Google Pixel": 800.0
        } 
        conn = get_connection()
        # Wir versuchen die Spalte 'preis' hinzuzufügen, falls sie noch nicht existiert (Migration)
        try:
            conn.execute("ALTER TABLE requests ADD COLUMN preis REAL")
        except:
            pass # Spalte existiert schon

        procure_req = pd.read_sql("SELECT * FROM requests WHERE status = 'Einkauf prüfen'", conn)
        
        # STATISTIK OBEN
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
                        # Preis-Vorschlag basierend auf der Referenzliste oder manuell
                        vorschlag = 0.0
                        for key in preise_ref:
                            if key.lower() in p_row['referenz_id'].lower():
                                vorschlag = preise_ref[key]
                        
                        einkaufspreis = st.number_input(f"Preis für {p_row['id']} (€)", 
                                                       value=vorschlag, step=50.0, key=f"price_{p_row['id']}")

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

# Hilfreiche Info für Tester in der Sidebar
with st.sidebar:
    st.divider()
    with st.expander("🔑 Demo-Zugänge"):
        st.code("Admin: admin123\nTech: tech123\nEinkauf: procure123")                        



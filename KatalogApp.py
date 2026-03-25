import streamlit as st
import pandas as pd
import sqlite3
import hmac
import json # Zentraler Import für alle Funktionen
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="The Core - IT Service Hub", layout="wide")

# --- 1. DATENBANK LOGIK ---
DB_FILE = "it_inventory_final.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Finale Tabellenstruktur mit 9 Spalten
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
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
    c.execute('''CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    beschreibung TEXT,
                    zielgruppe TEXT,
                    status TEXT,
                    standard_dauer TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anfrager TEXT,
                    abteilung TEXT,
                    typ TEXT,
                    referenz_id TEXT,
                    status TEXT,
                    erstellt_am TEXT,
                    letzte_aenderung TEXT,
                    kommentar TEXT
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
            ("SVC-001", "Adobe Creative Cloud", "Installation und Lizenzbereitstellung", "Alle", "aktiv", "2 Tage"),
            ("SVC-002", "VPN-Zugang", "Einrichtung für Homeoffice", "Alle", "aktiv", "1 Tag"),
            ("SVC-003", "Notebook-Einrichtung", "Software-Grundkonfiguration", "Vertrieb", "aktiv", "3 Tage"),
        ]
        c.executemany("INSERT INTO services VALUES (?,?,?,?,?,?)", sample_services)
        conn.commit()
    conn.close()

def init_inventory_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        # Technische Muster
        tech_srv = '{"IP": "192.168.10.15", "OS": "Ubuntu 22.04 LTS", "CPU": "2x Xeon Gold", "RAM": "128GB"}'
        tech_laptop = '{"CPU": "Apple M2 Max", "RAM": "32GB", "MAC": "00:1A:2B:3C:4D:5E"}'
        tech_zebra = '{"OS": "Android 13", "Engine": "SE4720", "IP-Rating": "IP65"}'

        sample_assets = [
            ("HW-IT-001", "ThinkPad X1 Carbon", "IT", "Lager", "-", "-", "SN-9921-X1", "01.2027", '{"RAM": "16GB"}'),
            ("HW-IT-002", "Dell PowerEdge R740", "IT", "In Benutzung", "Admin-Team", "25.03.2026", "SRV-DELL-01", "12.2028", tech_srv),
            ("HW-GR-001", "Mac Studio (M2)", "Grafik", "Lager", "-", "-", "APPLE-M2-088", "06.2027", tech_laptop),
            ("HW-VT-001", "iPhone 15 Pro", "Vertrieb", "Lager", "-", "-", "IMEI-334455", "10.2026", '{"MDM": "Active"}'),
            ("HW-LG-001", "Zebra TC52", "Logistik", "Lager", "-", "-", "ZEB-88120", "05.2026", tech_zebra),
            ("HW-GEN-001", "Logitech MX Master", "Alle", "Lager", "-", "-", "LOGI-992", "None", '{}')
        ]
        c.executemany("INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?,?)", sample_assets)
        conn.commit()
    conn.close()

# --- 2. SECURITY ---
def check_password():
    if st.session_state.get("password_correct"): return True
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
    st.warning("⚠️ Admin-Sperre aktiv.")
    st.text_input("Passwort", type="password", on_change=password_entered, key="password")
    return False

# --- 3. APP START ---
init_db()
init_sample_data()
init_inventory_data()

st.title("🛡️ BlueMarlin-IT-Profis – Service Hub")
# Hier sind jetzt alle drei Reiter definiert
tab_user, tab_admin, tab_tech = st.tabs(["🛒 Service Katalog", "⚙️ IT-Administration", "🛠️ Deep Tech (Techniker)"])

# --- USER TAB ---
with tab_user:
    st.sidebar.header("👤 Profil")
    u_name = st.sidebar.text_input("Dein Name", "Max Mustermann")
    u_dept = st.sidebar.selectbox("Abteilung", ["Vertrieb", "Grafik", "IT", "Buchhaltung", "Logistik"])
    
    anfrage_typ = st.radio("Was benötigst du?", ["Hardware", "Service"])
    df = load_data()
    
    if anfrage_typ == "Hardware":
        verfügbar = df[(df['abteilung'].isin([u_dept, "Alle"])) & (df['status'] == "Lager")]
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
        # --- HIER IST DIE ERSETZTE LOGIK FÜR SERVICES ---
        conn = get_connection()
        # Wir laden nur Services, die für die Abteilung des Users oder 'Alle' gedacht sind
        services_df = pd.read_sql("SELECT * FROM services WHERE zielgruppe IN (?, 'Alle')", conn, params=(u_dept,))
        conn.close()
        
        if services_df.empty:
            st.info("Keine spezifischen Dienstleistungen für deine Abteilung gefunden.")
        else:
            for _, s_row in services_df.iterrows():
                with st.container(border=True):
                    st.write(f"🛠️ **{s_row['name']}**")
                    st.caption(s_row['beschreibung'])
                    st.write(f"⏱️ Erwartete Dauer: {s_row['standard_dauer']}")
                    if st.button(f"Service buchen: {s_row['id']}", key=f"svc_{s_row['id']}"):
                        conn = get_connection()
                        conn.execute("INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am) VALUES (?,?,'service',?,'offen',?)",
                                     (u_name, u_dept, s_row['id'], datetime.now().strftime("%d.%m.%Y %H:%M")))
                        conn.commit(); conn.close()
                        st.toast(f"Anfrage für {s_row['name']} ist raus!")
                        st.rerun()
    # --- ANFRAGE-HISTORIE FÜR USER ---
    st.divider()
    st.subheader("📋 Meine letzten Anfragen")
    conn = get_connection()
    # Wir holen uns die Details zu den Anfragen des aktuellen Nutzers
    history_df = pd.read_sql("""
        SELECT r.typ, r.referenz_id, r.status, r.erstellt_am 
        FROM requests r 
        WHERE r.anfrager = ? 
        ORDER BY r.erstellt_am DESC LIMIT 5
    """, conn, params=(u_name,))
    conn.close()

    if not history_df.empty:
        # Ein bisschen Styling für die Status-Anzeige
        def color_status(val):
            color = 'orange' if val == 'offen' else 'green' if val == 'genehmigt' else 'red'
            return f'color: {color}; font-weight: bold'
        
        st.table(history_df.style.map(color_status, subset=['status']))
    else:
        st.caption("Du hast noch keine Anfragen gestellt.")
# --- ADMIN TAB ---
with tab_admin:
    if check_password():
        st.header("🛠️ Management Konsole")
        df_admin = load_data()
        
        st.subheader("🚥 Asset Health Check (Garantie)")
        today = datetime.now()
        critical_count, warning_count = 0, 0
        
        for _, row in df_admin.iterrows():
            g_date_str = row['garantie_bis']
            if g_date_str and g_date_str not in ["None", "-", ""]:
                try:
                    # Datum parsen (wir hängen .01 an für den ersten des Monats)
                    g_date = datetime.strptime(f"01.{g_date_str}", "%d.%m.%Y")
                    # Differenz in Tagen
                    diff_days = (g_date - today).days
                    
                    if diff_days < 0:
                        critical_count += 1
                    elif diff_days <= 180: # 6 Monate
                        warning_count += 1
                except: continue

        a1, a2, a3 = st.columns(3)
        a1.error(f"🔴 Kritisch: {critical_count}")
        a2.warning(f"🟡 Warning: {warning_count}")
        a3.success(f"🟢 Gesund: {len(df_admin) - critical_count - warning_count}")
        
        if critical_count > 0:
            st.error(f"⚠️ Handlungsbedarf: {critical_count} Garantien abgelaufen!")
        
        st.divider()
        
        # --- SUCHE & FILTER ---
        c_search, c_filter = st.columns([2, 1])
        with c_search:
            search_term = st.text_input("🔍 Suche (ID, Typ, Besitzer...)", "")
        with c_filter:
            # Ein einfacher Filter für die Ampel-Logik
            filter_mode = st.selectbox("Filter", ["Alle anzeigen", "Nur Kritische (Abgelaufen)", "Nur Wartung (Gelb)"])

        # Daten filtern basierend auf Suche
        display_df = df_admin.copy()
        if search_term:
            display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
        
        # Daten filtern basierend auf Ampel-Status
        if filter_mode != "Alle anzeigen":
            # Hier nutzen wir eine kleine Hilfsfunktion für den Filter
            def check_status(date_str):
                try:
                    d = datetime.strptime(f"01.{date_str}", "%d.%m.%Y")
                    diff = (d - today).days
                    if filter_mode == "Nur Kritische (Abgelaufen)": return diff < 0
                    if filter_mode == "Nur Wartung (Gelb)": return 0 <= diff <= 180
                except: return False
                return False
            
            display_df = display_df[display_df['garantie_bis'].apply(check_status)]

        st.dataframe(display_df, use_container_width=True)

        # --- EXPORT BEREICH (Deine optimierte Version) ---
        st.divider()
        if not df_admin.empty:
            export_df = df_admin.copy()
            try:
                processed_tech = []
                for val in export_df['details_json']:
                    if isinstance(val, str) and val.strip().startswith('{'):
                        try: processed_tech.append(json.loads(val))
                        except: processed_tech.append({})
                    else: processed_tech.append({})
                
                tech_df = pd.json_normalize(processed_tech)
                tech_df.index = export_df.index
                final_df = pd.concat([export_df.drop(columns=['details_json']), tech_df], axis=1)
                
                csv = final_df.to_csv(index=False, sep=";", encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("🚀 Excel-Export (Smart)", data=csv, file_name="IT_Inventur.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Export-Fehler: {e}")

        # --- NEUES ASSET (Fix: Jetzt mit 9 Spalten!) ---
        with st.expander("➕ Neues Asset registrieren"):
            with st.form("new_asset"):
                f1, f2, f3 = st.columns(3)
                nid = f1.text_input("ID (z.B. HW-005)")
                ntyp = f2.text_input("Modell (z.B. iPhone 15)")
                nabt = f3.selectbox("Ziel", ["Alle", "IT", "Grafik", "Vertrieb", "Logistik"])
                
                f4, f5 = st.columns(2)
                n_sn = f4.text_input("Seriennummer")
                n_gar = f5.text_input("Garantie bis (MM.YYYY)", placeholder="12.2026")
                
                if st.form_submit_button("In CMDB aufnehmen"):
                    if nid and ntyp:
                        conn = get_connection()
                        # Jetzt werden alle 9 Spalten sauber befüllt
                        conn.execute("INSERT INTO inventory VALUES (?,?,?, 'Lager', '-', '-', ?, ?, '{}')", 
                                     (nid, ntyp, nabt, n_sn, n_gar))
                        conn.commit()
                        conn.close()
                        st.success(f"Asset {nid} registriert!")
                        st.rerun()
                    else:
                        st.error("Bitte ID und Modell angeben.")

# --- TECH TAB ---
with tab_tech:
    if check_password():
        st.header("🔍 Technisches Dossier")
        df_tech = load_data()
        target = st.selectbox("Asset wählen", df_tech['id'].tolist())
        if target:
            item = df_tech[df_tech['id'] == target].iloc[0]
            st.subheader(f"Konfiguration für {item['typ']}")
            try:
                d = json.loads(item['details_json'])
                for k, v in d.items(): st.info(f"**{k}**: {v}")
            except: st.write("Keine technischen Details hinterlegt.")
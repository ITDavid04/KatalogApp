import streamlit as st #für die Web-App-Entwicklung
import pandas as pd #für Datenmanipulation und Anzeige
import sqlite3 #für persistente Datenbank
import hmac #für sichere Passwortprüfung
from datetime import datetime #für Zeitstempel bei Anfragen und Updates

# --- CONFIG & STYLING ---
st.set_page_config(page_title="The Core - IT Service Hub", layout="wide") # Seiteneinstellungen: Titel und Layout

# --- 1. DATENBANK LOGIK (PERSISTENTE CMDB) ---
DB_FILE = "it_inventory_final.db" # Dateiname für die SQLite-Datenbank, die die CMDB und Anfragen speichert

def get_connection(): # Funktion, um eine Verbindung zur SQLite-Datenbank herzustellen
    return sqlite3.connect(DB_FILE) # Rückgabe eines Verbindungsobjekts

def init_db(): # Funktion, um die Datenbank zu initialisieren und die benötigten Tabellen zu erstellen
    conn = get_connection() # Verbindung zur Datenbank herstellen
    c = conn.cursor() # Cursor-Objekt für SQL-Befehle
    # Tabelle für Hardware & Services (erweitert um Seriennummer, Garantie)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id TEXT PRIMARY KEY,
                    typ TEXT,
                    abteilung TEXT,
                    status TEXT,
                    besitzer TEXT,
                    last_update TEXT,
                    seriennummer TEXT,
                    garantie_bis TEXT
                )''')
    # Tabelle für Dienstleistungen
    c.execute('''CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    beschreibung TEXT,
                    zielgruppe TEXT,
                    status TEXT,  -- 'aktiv', 'inaktiv'
                    standard_dauer TEXT
                )''')
    # Tabelle für Anfragen (Tickets)
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anfrager TEXT,
                    abteilung TEXT,
                    typ TEXT,          -- 'asset' oder 'service'
                    referenz_id TEXT,  -- ID aus inventory oder services
                    status TEXT,       -- 'offen', 'genehmigt', 'abgelehnt', 'erledigt'
                    erstellt_am TEXT,
                    letzte_aenderung TEXT,
                    kommentar TEXT
                )''')
    conn.commit()
    conn.close()

def load_data(): # Funktion, um die gesamte inventory-Tabelle als DataFrame zu laden
    """Lädt die gesamte inventory-Tabelle als DataFrame."""
    conn = get_connection() # Verbindung zur Datenbank herstellen
    df = pd.read_sql("SELECT * FROM inventory", conn)
    conn.close()
    return df

def init_sample_data(): # Funktion, um Beispieldaten für Services einzufügen, falls die Tabelle leer ist
    """Fügt Beispieldaten für Services ein, falls Tabelle leer."""
    conn = get_connection()
    c = conn.cursor()
    # Prüfen, ob Services vorhanden
    c.execute("SELECT COUNT(*) FROM services")
    count = c.fetchone()[0]
    if count == 0:
        # Ein paar Beispielservices
        sample_services = [
            ("SVC-001", "Adobe Creative Cloud", "Installation und Lizenzbereitstellung für Adobe CC", "Alle", "aktiv", "2 Tage"),
            ("SVC-002", "VPN-Zugang", "Einrichtung eines VPN-Zugangs für Homeoffice", "Alle", "aktiv", "1 Tag"),
            ("SVC-003", "Notebook-Einrichtung", "Erstausstattung eines neuen Notebooks mit Software", "Vertrieb", "aktiv", "3 Tage"),
        ]
        c.executemany("INSERT INTO services VALUES (?,?,?,?,?,?)", sample_services)
        conn.commit()
    conn.close()

# --- 2. SECURITY (ADMIN LOCK) ---
def check_password():
    """Gibt True zurück, wenn das Passwort korrekt eingegeben wurde."""
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    st.warning("⚠️ Zugriff verweigert. Bitte Admin-Passwort eingeben.")
    st.text_input("Passwort (Standard: admin123)", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Falsches Passwort.")
    return False

# --- 3. APP INITIALISIERUNG ---
init_db() #Datenbank initialisieren (Tabellen erstellen, falls nicht vorhanden)
init_sample_data()   # Beispieldaten für Services

st.title("🛡️ The Core – IT Service Hub")
st.caption("Verbindung von Business-Service-Katalog und technischer CMDB")

# Tabs für die Trennung der Welten
tab_user, tab_admin = st.tabs(["🛒 Service Katalog (User)", "⚙️ IT-Administration (CMDB)"])

# --- USER BEREICH (BUSINESS VIEW) ---
with tab_user:# Sidebar für Benutzerprofil (wie im Original)
    # Sidebar für Benutzerprofil (wie im Original)
    st.sidebar.header("👤 Benutzer-Profil")
    u_name = st.sidebar.text_input("Dein Name", "Max Mustermann")
    u_dept = st.sidebar.selectbox("Abteilung", ["Vertrieb", "Grafik", "IT", "Buchhaltung", "Logistik"])
    
    st.header(f"Hallo {u_name}, was benötigst du heute?")

    # Auswahl: Hardware oder Service?
    anfrage_typ = st.radio("Art der Anfrage", ["Hardware bestellen", "Dienstleistung anfordern"])

    if anfrage_typ == "Hardware bestellen":
        df = load_data()
        # Achtung: Hier muss 'Lager' Status haben; die ursprüngliche Tabelle hatte 'Lager'
        verfügbar = df[(df['abteilung'].isin([u_dept, "Alle"])) & (df['status'] == "Lager")]
        if verfügbar.empty:
            st.info("Aktuell keine Hardware für deine Abteilung verfügbar.")
        else:
            st.subheader("Verfügbare Geräte")
            for _, row in verfügbar.iterrows():
                with st.container(border=True):
                    st.write(f"**{row['typ']}** (ID: {row['id']})")
                    if st.button(f"Anfordern: {row['typ']}", key=f"req_{row['id']}"):
                        conn = get_connection()
                        conn.execute("""
                            INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am, letzte_aenderung)
                            VALUES (?, ?, 'asset', ?, 'offen', ?, ?)
                        """, (u_name, u_dept, row['id'],
                              datetime.now().strftime("%d.%m.%Y %H:%M"),
                              datetime.now().strftime("%d.%m.%Y %H:%M")))
                        conn.commit()
                        conn.close()
                        st.toast(f"Anfrage für {row['typ']} wurde gesendet!")
                        st.rerun()
    else:
        # Dienstleistungen anzeigen
        conn = get_connection()
        services_df = pd.read_sql("SELECT * FROM services WHERE zielgruppe IN (?, 'Alle') AND status='aktiv'", conn, params=(u_dept,))
        conn.close()
        if services_df.empty:
            st.info("Keine Dienstleistungen für deine Abteilung verfügbar.")
        else:
            st.subheader("Dienstleistungen")
            for _, row in services_df.iterrows():
                with st.container(border=True):
                    st.write(f"**{row['name']}**")
                    st.caption(row['beschreibung'])
                    if st.button(f"Dienstleistung anfordern: {row['name']}", key=f"req_svc_{row['id']}"):
                        conn = get_connection()
                        conn.execute("""
                            INSERT INTO requests (anfrager, abteilung, typ, referenz_id, status, erstellt_am, letzte_aenderung)
                            VALUES (?, ?, 'service', ?, 'offen', ?, ?)
                        """, (u_name, u_dept, row['id'],
                              datetime.now().strftime("%d.%m.%Y %H:%M"),
                              datetime.now().strftime("%d.%m.%Y %H:%M")))
                        conn.commit()
                        conn.close()
                        st.toast(f"Anfrage für {row['name']} wurde gesendet!")
                        st.rerun()

    # Meine offenen Anfragen anzeigen
    with st.expander("📋 Meine offenen Anfragen"):
        conn = get_connection()
        meine_anfragen = pd.read_sql("""
            SELECT r.*, 
                   CASE WHEN r.typ='asset' THEN i.typ ELSE s.name END as bezeichnung
            FROM requests r
            LEFT JOIN inventory i ON r.typ='asset' AND r.referenz_id=i.id
            LEFT JOIN services s ON r.typ='service' AND r.referenz_id=s.id
            WHERE anfrager=?
            ORDER BY erstellt_am DESC
        """, conn, params=(u_name,))
        conn.close()
        if not meine_anfragen.empty:
            st.dataframe(meine_anfragen[['bezeichnung', 'status', 'erstellt_am', 'letzte_aenderung']], use_container_width=True)
        else:
            st.write("Noch keine Anfragen gestellt.")

# --- ADMIN BEREICH (TECHNICAL VIEW / CMDB) ---
with tab_admin:
    st.header("🛠️ IT-Management Konsole")
    
    if check_password():
        st.success("Admin-Modus aktiv.")
        
        # 1. Dashboard Kennzahlen
        df_admin = load_data()
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt-Assets", len(df_admin))
        c2.metric("Im Lager", len(df_admin[df_admin['status'] == "Lager"]))
        c3.metric("Im Einsatz", len(df_admin[df_admin['status'] == "In Benutzung"]))
        
        # 2. Suche & Filter (Power-User Tools)
        st.divider()
        st.subheader("Bestand durchsuchen")
        search_term = st.text_input("Suche nach ID, Typ oder Besitzer...")
        if search_term:
            filtered_df = df_admin[
                df_admin.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            ]
        else:
            filtered_df = df_admin
        st.dataframe(filtered_df, use_container_width=True)
        
        # 3. Anfragen verwalten
        st.divider()
        st.subheader("📋 Anfragen verwalten")
        conn = get_connection()
        offene_anfragen = pd.read_sql("""
            SELECT r.*, 
                   CASE WHEN r.typ='asset' THEN i.typ ELSE s.name END as bezeichnung
            FROM requests r
            LEFT JOIN inventory i ON r.typ='asset' AND r.referenz_id=i.id
            LEFT JOIN services s ON r.typ='service' AND r.referenz_id=s.id
            WHERE r.status='offen'
            ORDER BY erstellt_am
        """, conn)
        conn.close()
        if offene_anfragen.empty:
            st.info("Keine offenen Anfragen.")
        else:
            for idx, row in offene_anfragen.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{row['bezeichnung']}** (Anfrager: {row['anfrager']}, Abt: {row['abteilung']})")
                        st.caption(f"Eingegangen: {row['erstellt_am']}")
                    with col2:
                        col2_1, col2_2 = st.columns(2)
                        with col2_1:
                            if st.button("✅ Genehmigen", key=f"approve_{row['id']}"):
                                conn = get_connection()
                                conn.execute("UPDATE requests SET status='genehmigt', letzte_aenderung=? WHERE id=?", 
                                             (datetime.now().strftime("%d.%m.%Y %H:%M"), row['id']))
                                # Bei Asset: falls Hardware, Status im inventory auf "In Benutzung" setzen
                                if row['typ'] == 'asset':
                                    conn.execute("UPDATE inventory SET status='In Benutzung', besitzer=?, last_update=? WHERE id=?", 
                                                 (row['anfrager'], datetime.now().strftime("%d.%m.%Y %H:%M"), row['referenz_id']))
                                conn.commit()
                                conn.close()
                                st.success(f"Anfrage {row['id']} genehmigt.")
                                st.rerun()
                        with col2_2:
                            if st.button("❌ Ablehnen", key=f"reject_{row['id']}"):
                                conn = get_connection()
                                conn.execute("UPDATE requests SET status='abgelehnt', letzte_aenderung=? WHERE id=?", 
                                             (datetime.now().strftime("%d.%m.%Y %H:%M"), row['id']))
                                conn.commit()
                                conn.close()
                                st.warning(f"Anfrage {row['id']} abgelehnt.")
                                st.rerun()
        
        # --- EXPORT FUNKTION (FINISHER) ---
        st.divider()
        st.subheader("📊 Reporting")
        csv = df_admin.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Gesamtes Inventar als CSV exportieren",
            data=csv,
            file_name=f"IT_Inventur_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            help="Klicke hier, um die aktuelle CMDB für Excel herunterzuladen."
        )
        
        # 4. Bestands-Pflege (Provisioning)
        with st.expander("➕ Neues Asset registrieren"):
            with st.form("new_asset_form"):
                f1, f2, f3 = st.columns(3)
                nid = f1.text_input("ID (z.B. HW-2026-001)")
                ntyp = f2.text_input("Geräte-Typ (z.B. Dell XPS 15)")
                nabt = f3.selectbox("Zielgruppe", ["Alle", "Grafik", "IT", "Vertrieb", "Buchhaltung"])
                # Zusätzliche Felder für Seriennummer und Garantie
                seriennummer = st.text_input("Seriennummer (optional)")
                garantie_bis = st.text_input("Garantie bis (optional, z.B. 12.2027)")
                
                if st.form_submit_button("In CMDB aufnehmen"):
                    if nid and ntyp:
                        try:
                            conn = get_connection()
                            # Alle 8 Spalten füllen (bei optionalen Feldern leere Strings)
                            conn.execute("""
                                INSERT INTO inventory (id, typ, abteilung, status, besitzer, last_update, seriennummer, garantie_bis)
                                VALUES (?, ?, ?, 'Lager', '-', '-', ?, ?)
                            """, (nid, ntyp, nabt, seriennummer, garantie_bis))
                            conn.commit()
                            conn.close()
                            st.success("Gerät erfolgreich im System registriert.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Fehler: ID bereits vergeben!")
                    else:
                        st.warning("Bitte ID und Typ ausfüllen.")

        # 5. Daten-Wartung
        with st.expander("⚠️ System-Wartung"):
            if st.button("Inventar komplett löschen"):
                conn = get_connection()
                conn.execute("DELETE FROM inventory")
                conn.commit()
                conn.close()
                st.rerun()
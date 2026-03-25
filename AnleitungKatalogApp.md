markdown

# 📘 BlueMarlin IT Service Hub – Dokumentation  

### Ein Leitfaden für IT-Umschüler & Junior-Entwickler

Diese App ist ein **praxisnahes Beispiel** für eine moderne **Full-Stack-Anwendung** mit **Python** und **Streamlit**. Sie zeigt, wie ein kleiner IT‑Service‑Hub funktionieren kann, in dem Mitarbeiter Geräte anfordern, Administratoren genehmigen und der Einkauf Bestellungen auslöst. Gleichzeitig lernst du wichtige Konzepte kennen, die in vielen IT‑Projekten vorkommen: Datenbanken, Benutzerrollen, dynamische Berechnungen und sichere Passwortprüfung.

---

## 1. Architektur – Was passiert wo?

Die Anwendung besteht aus drei Schichten:

| Schicht          | Aufgabe                                                                 | Technologie                 |
|------------------|-------------------------------------------------------------------------|-----------------------------|
| **Frontend**     | Zeigt die Benutzeroberfläche an und reagiert auf Klicks / Eingaben.      | **Streamlit** (Python)      |
| **Backend‑Logik**| Entscheidet, welche Daten angezeigt werden, ob Passwörter korrekt sind, und führt Workflows aus. | **Python**                  |
| **Datenbank**    | Speichert alle Daten dauerhaft (Inventar, Services, Anfragen).          | **SQLite** (Datei‑Datenbank) |

Streamlit führt das Python‑Skript bei jeder Aktion **neu aus**. Damit die App trotzdem weiß, ob ein Benutzer eingeloggt ist, nutzen wir den sogenannten **Session State** (mehr dazu im Deep Dive).

---

## 2. Workflow – Von der Anfrage bis zur Bestellung

1. **Mitarbeiter (User)**  
    – Öffnet die App und wählt im Tab *Service Katalog* ein Gerät oder einen Service aus.  
    – Die App schreibt einen Datensatz in die Tabelle `requests` mit dem Status **offen**.

2. **IT‑Leiter (Admin)**  
    – Öffnet den Tab *IT‑Administration* und sieht alle offenen Anfragen.  
    – Kann eine Anfrage **genehmigen** (Status `genehmigt` – das Gerät wird im Inventar dem Mitarbeiter zugewiesen) oder  
    – **zur Beschaffung weiterleiten** (Status `Einkauf prüfen`).

3. **Einkauf (Procurement)**  
    – Im Tab *Beschaffungs-Management* sieht er nur Anfragen mit dem Status `Einkauf prüfen`.  
    – Er gibt einen Preis ein und bestellt das Gerät (Status `In Bestellung`).  
    – Der Preis fließt in das Ausgaben‑Dashboard ein.

4. **Reporting**  
   – Alle Statusänderungen und Preise sind sofort in den Dashboards sichtbar.

> **Warum ist das wichtig?** > Du siehst, wie sich Daten über verschiedene Rollen und Phasen bewegen – ein echtes **Workflow‑Beispiel** aus der Praxis.

---

## 3. Deep Dive – Technische Konzepte im Detail

### a) Dynamische Daten mit JSON

**Problem:** Jedes IT‑Gerät hat andere technische Details. Ein Monitor hat eine Bildschirmgröße, ein Server **CPU** und **RAM**, ein Tablet eine Schutzklasse. Eine feste Tabellenstruktur mit vielen Spalten wäre unflexibel.

**Lösung:** In der Spalte `details_json` wird ein ****JSON**‑String** gespeichert. **JSON** ist ein einfaches Textformat, das wie ein Python‑Wörterbuch (Dictionary) aufgebaut ist.

**Beispiel aus dem Code:** ```python # Speichern: '{*IP*: ***192**.**168**.10.15*, *OS*: *Ubuntu 22.04*, *CPU*: *2x Xeon*}'

# Später auslesen und als Python-Objekt verwenden:

details = json.loads(item['details_json'])
for key, value in details.items():
    st.info(f*{key}: {value}*)

Lerneffekt: Du verstehst, wie man mit flexiblen Datenstrukturen arbeitet, ohne die Datenbank ständig umzubauen. **JSON** wird heute überall eingesetzt – von Konfigurationsdateien bis zu **API**‑Antworten.
- Die Garantie‑Ampel – Dynamische Berechnungen mit Datum

Die App zeigt im Admin‑Bereich farbig an, wie es um die Garantie der Geräte steht. Dafür wird das aktuelle Datum mit dem Garantieende verglichen.

Schritte:

    Das Garantieende liegt als Text in der Spalte garantie_bis vor, z. B. *01.**2027***.

    Mit datetime.strptime wird daraus ein echtes Datumsobjekt gemacht.

    Die Differenz in Tagen zum heutigen Datum wird berechnet.

    Je nach Differenz wird ein Emoji (🔴, 🟡, 🟢) und eine **CSS**‑Klasse vergeben.

Code‑Ausschnitt: python

def get_garantie_status(garantie_str):
    if not garantie_str or garantie_str in [*None*, *-*, "*]:
    return *⚪ Unbekannt"
    try:
    garantie_date = datetime.strptime(f*01.{garantie_str}*, *%d.%m.%Y*)
    diff = (garantie_date - datetime.now()).days
    if diff < 0: return *🔴 Kritisch*
    if diff <= **180**: return *🟡 Warnung*
    return *🟢 Gesund*
    except:
    return *⚪ Unbekannt*

Lerneffekt: Hier lernst du Datums‑ und Zeitberechnungen – ein unverzichtbares Werkzeug für IT‑Administratoren, z. B. für Lizenz‑ oder Zertifikatsabläufe.
- Session State & sichere Passwortprüfung (**HMAC**)

Streamlit führt das Skript bei jedem Klick neu aus. Damit die App weiß, ob ein Benutzer bereits eingeloggt ist, nutzen wir st.session_state. Das ist wie ein kurzzeitiger Speicher für die aktuelle Browsersitzung.

Authentifizierungs‑Funktion: python

def authenticate(role: str) -> bool:
    auth_key = f*auth_{role}*
    if st.session_state.get(auth_key):
    return True

    def check_password():
    if hmac.compare_digest(st.session_state[f*pw_{role}*], **PASSWORDS**[role]):
    st.session_state[auth_key] = True
    del st.session_state[f*pw_{role}*]
    else:
    st.error(*❌ Passwort falsch*)

    st.text_input(f*Passwort für {role}*, type=*password*, key=f*pw_{role}*, on_change=check_password)
    return False

Wichtig:

    Der Passwortvergleich erfolgt mit hmac.compare_digest – das ist sicherer als ein einfaches ==, weil es gegen Timing‑Angriffe schützt.

    Der Session‑State speichert den Login‑Status, damit nicht bei jedem Klick erneut das Passwort abgefragt wird.

Lerneffekt: Du lernst, wie State‑Management in Web‑Apps funktioniert und warum Sicherheit bei Passwörtern entscheidend ist.
- **SQL** + Pandas – Daten im Überblick

Statt jede Zeile der Datenbank einzeln zu verarbeiten, nutzt der Code Pandas, um die gesamte Tabelle in einen DataFrame zu laden. Ein DataFrame ist wie ein Tabellenblatt in Excel, nur in Python.

Beispiel: python

df_inv = load_inventory()           # Lädt die ganze Tabelle *inventory* available = df_inv[(df_inv['abteilung'] == user_dept) & (df_inv['status'] == *Lager*)]

Mit einem DataFrame kannst du:

    filtern (df[df['status'] == 'Lager'])

    sortieren

    statistische Werte berechnen (z. B. df['preis'].sum())

Lerneffekt: Du erkennst, wie man mit Pandas große Datenmengen kompakt und performant verarbeitet – ein Muss in der Datenanalyse und im Reporting. ## Erste Schritte – So startest du die App

    Repository klonen oder die Python‑Datei speichern
    Lege eine Datei, z. B. app.py, an und kopiere den Code aus dem Projekt hinein.

    Abhängigkeiten installieren
    Öffne ein Terminal und führe aus:
    bash

    pip install streamlit pandas

    Hinweis: sqlite3 und hmac sind bereits in Python enthalten.

    App starten
    bash

    streamlit run app.py

    Streamlit öffnet automatisch einen Browser‑Tab.

    Demo‑Zugänge ausprobieren

        Admin: Passwort admin123

        Techniker: Passwort tech123

        Einkauf: Passwort procure123

5. Übungsaufgaben – Mach die App zu deinem eigenen Projekt

Um das Gelernte zu vertiefen, kannst du folgende Erweiterungen umsetzen:
Aufgabe	Was du lernst
## Validierung	Verhindere, dass im Formular „Asset registrieren“ leere Felder abgeschickt werden. Zeige eine Fehlermeldung.
## Erweiterte Suche	Baue die globale Suche so um, dass sie auch in den JSON‑Details (details_json) sucht.
## Audit‑Log	Speichere in einer neuen Tabelle audit_log, wer wann welche Anfrage genehmigt oder bestellt hat.
## E‑Mail‑Benachrichtigung	Sende bei Statusänderungen (z. B. Genehmigung) eine E‑Mail an den Anfrager (nutze z. B. smtplib).
## Dashboard‑Filter	Erweitere das Finanz‑Dashboard um einen Filter, der nur Bestellungen eines bestimmten Monats anzeigt.
Fazit

Mit dieser kleinen, aber vollständigen Anwendung hast du gelernt, wie man mit Python, Streamlit und SQLite eine echte Unternehmens‑Anwendung baut. Du kennst jetzt wichtige Konzepte wie **JSON**‑Speicherung, dynamische Berechnungen, Rollen‑ und State‑Management sowie Datenanalyse mit Pandas.

Nutze das Projekt als Sprungbrett für deine eigenen Ideen – und scheue dich nicht, den Code zu ändern, zu erweitern und zu verbessern. Genau so wächst man als Entwickler! text

Speichere diesen Text in einer Datei mit der Endung `.md` (z. B. `**README**.md` oder `**DOKUMENTATION**.md`) in deinem Repository.
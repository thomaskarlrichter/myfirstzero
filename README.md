# Komitee-App – Plattform für strukturierte Gruppenarbeit

Die Komitee-App ist eine Webanwendung für die Dokumentation und Organisation von Komitee-Treffen basiernd auf den Prinzipien der 12-Schritte-Programme. Sie ermöglicht Mitgliedern, persönliche Auflagen (Fastenvereinbarungen), Rückfälle und Wortmeldungen zu strukturierten Treffen zu erfassen und zu verwalten.

## ✨ Funktionen

### 👥 **Benutzerverwaltung**
- Registrierung und Anmeldung
- Persönliches Profil
- Passwortgeschützte Sessions

### 💬 **Wortmeldungen**
- Erstellen von Wortmeldungen mit Kategorien:
  1. **Vorfall** – Allgemeine Vorkommnisse
  2. **Rückfall** – Bezug auf vorhandene Auflagen
  3. **Mitteilung zu einer Auflage** – Updates zu Fastenvereinbarungen
  4. **Geheimnis offenbaren** – Persönliche Mitteilungen
  5. **Beziehungsklärung mit XYZ** – Konfliktlösung
- Status-System: `offen`, `erledigt`, `zurückgestellt`, `gelöscht`
- Zuordnung zu spezifischen Treffen

### 📅 **Treffen-Verwaltung**
- Erstellen von Komitee-Treffen mit:
  - Datum und Uhrzeit
  - Ort
  - Beschreibung (optional)
- Übersicht aller geplanten und vergangenen Treffen
- Detailansicht mit allen angemeldeten Wortmeldungen
- Bearbeiten und Löschen von Treffen

### 📋 **Auflagen/Fastenvereinbarungen**
- Erstellen persönlicher Auflagen mit:
  - Beschreibung, Grund und Ziel
  - Zeitraum (Start- und Enddatum)
  - Erfahrungen (optional)
- Übersicht aller eigenen Auflagen
- Detailansicht mit zugehörigen Rückfällen
- Bearbeiten und Löschen

### 🔄 **Rückfälle**
- Dokumentation von Rückfällen innerhalb einer Auflage
- Erfassen von:
  - Beschreibung
  - Gefühlen
  - Situation
  - Lernpunkten (optional)
  - Positivem Verhalten (optional)
- Verknüpfung mit spezifischer Auflage

### 🛠️ **Technische Features**
- **Flask-basiert** mit SQLAlchemy ORM
- **Datenbank-Migrationen** mit Flask-Migrate
- **CSRF-Schutz** für alle Formulare
- **Responsive Design** mit Bootstrap 5
- **Rollenbasierte Navigation** (authentifizierte vs. anonyme Benutzer)
- **Externer Zugriff** via Localtunnel

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.8+
- pip
- SQLite (enthalten)

### Installation
```bash
# Repository klonen
cd /a0/usr/projects/die_komitee_app

# Virtuelle Umgebung erstellen und aktivieren
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Datenbank initialisieren
flask db upgrade

# App starten
python3 -m flask run --host=0.0.0.0 --port=8080
```

### Externer Zugriff (Localtunnel)
```bash
# Tunnel starten
lt --port 8080 --subdomain diekomitee
```

Die App ist dann unter **https://diekomitee.loca.lt** erreichbar.

## 📁 Datenmodelle

### User
- `id`, `username`, `email`, `password_hash`, `erstellt_am`
- Beziehungen zu: `wortmeldungen`, `rueckmeldungen`, `auflagen`

### Wortmeldung
- `id`, `text`, `kategorie`, `status`, `datum_uhrzeit`, `user_id`, `treffen_id`
- Beziehung zu: `user` (Autor), `treffen`, `rueckmeldungen`

### Treffen
- `id`, `datum`, `uhrzeit`, `ort`, `beschreibung`, `erstellt_am`
- Beziehung zu: `wortmeldungen`

### Auflage
- `id`, `beschreibung`, `grund`, `ziel`, `zeitraum_start`, `zeitraum_ende`, `erfahrungen`, `erstellt_am`, `user_id`
- Beziehung zu: `user`, `rueckfaelle`

### Rueckfall
- `id`, `beschreibung`, `gefuehle`, `situation`, `lernpunkte`, `positives_verhalten`, `datum_uhrzeit`, `auflage_id`, `user_id`
- Beziehung zu: `auflage`, `user`

### Rueckmeldung
- `id`, `text`, `datum_uhrzeit`, `user_id`, `wortmeldung_id`
- Beziehung zu: `user` (Autor), `wortmeldung`

## 🔧 API-Endpunkte

### Authentifizierung
- `GET/POST /register` – Benutzerregistrierung
- `GET/POST /login` – Anmeldung
- `GET /logout` – Abmeldung
- `GET /profile/<username>` – Profil anzeigen

### Wortmeldungen
- `GET /` – Alle Wortmeldungen (Startseite)
- `GET/POST /wortmeldung/neu` – Neue Wortmeldung
- `GET /wortmeldung/<id>` – Wortmeldungs-Detail
- `GET/POST /wortmeldung/<id>/bearbeiten` – Bearbeiten
- `POST /wortmeldung/<id>/loeschen` – Löschen
- `GET/POST /wortmeldung/<id>/rueckmeldung/neu` – Rückmeldung hinzufügen

### Auflagen
- `GET /auflagen` – Übersicht aller Auflagen
- `GET/POST /auflage/neu` – Neue Auflage
- `GET /auflage/<id>` – Auflage-Detail mit Rückfällen
- `GET/POST /auflage/<id>/bearbeiten` – Bearbeiten
- `POST /auflage/<id>/loeschen` – Löschen

### Rückfälle
- `GET/POST /auflage/<auflage_id>/rueckfall/neu` – Neuer Rückfall
- `GET/POST /rueckfall/<id>/bearbeiten` – Rückfall bearbeiten
- `POST /rueckfall/<id>/loeschen` – Rückfall löschen

### Treffen
- `GET /treffen` – Alle Treffen
- `GET/POST /treffen/neu` – Neues Treffen
- `GET /treffen/<id>` – Treffen-Detail mit Wortmeldungen
- `GET/POST /treffen/<id>/bearbeiten` – Treffen bearbeiten
- `POST /treffen/<id>/loeschen` – Treffen löschen
- `GET/POST /treffen/<treffen_id>/wortmeldung/neu` – Wortmeldung zu Treffen anmelden

## 🎨 Templates

- `base.html` – Grundlayout mit Navigation
- `index.html` – Startseite mit Wortmeldungen
- `login.html`, `register.html`, `profile.html` – Authentifizierung
- `wortmeldung*.html` – Wortmeldungs-Verwaltung
- `auflage*.html` – Auflagen-Verwaltung
- `rueckfall*.html` – Rückfall-Verwaltung
- `treffen*.html` – Treffen-Verwaltung
- `wortmeldung_treffen_neu.html` – Wortmeldung zu Treffen anmelden

## 🔒 Sicherheit

- **Passwort-Hashing** mit Werkzeug
- **CSRF-Schutz** für alle POST-Formulare
- **Session-basierte Authentifizierung**
- **Autorisierung** (nur eigene Inhalte bearbeiten/löschen)

## 📈 Status-System für Wortmeldungen

Jede Wortmeldung hat einen von vier Statuswerten:
1. **offen** – Standard bei Erstellung
2. **erledigt** – Von Komiteeleitung als abgeschlossen markiert
3. **zurückgestellt** – Für später verschoben
4. **gelöscht** – Nicht mehr relevant (soft delete)

## 🌐 Externer Zugriff

Die App kann über Localtunnel öffentlich erreichbar gemacht werden:
```bash
lt --port 8080 --subdomain diekomitee
```

Danach erreichbar unter: **https://diekomitee.loca.lt**

## 🚧 Geplante Erweiterungen

1. **Zugriffskontrolle** – Komiteeleitung kann Status von Wortmeldungen ändern
2. **Export-Funktion** – PDF/CSV-Listen für Treffen
3. **Benachrichtigungen** – Erinnerungen an bevorstehende Treffen
4. **Teilnehmer-Verwaltung** – Wer nimmt an Treffen teil?
5. **Statistiken** – Übersicht über Auflagen und Rückfälle

## 📄 Lizenz

Dieses Projekt ist für den internen Gebrauch der Komitee-Gruppe entwickelt worden.

## 👥 Beitragende

- **Agent Zero** – Implementierung
- **Komitee-Mitglieder** – Konzept und Anforderungen

---

**Letzte Aktualisierung**: April 2026  
**Version**: 0.3 (mit Treffen-Funktionalität)  
**Status**: Produktiv einsatzbereit

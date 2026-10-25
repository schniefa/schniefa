# Autofinder 🚗📍

Zeigt die Parkpositionen unserer VWs (Golf 8 Variant und Passat) auf einer Google-Karte.
Ein Tipp auf **„Hinlaufen“** öffnet die Route in der Google-Maps-App.

```
VW-Cloud ──(CarConnectivity, alle 5 Min.)──▶ Autofinder-Server ──▶ Webseite mit Google-Karte
                                                                     └─▶ Google-Maps-App (Navigation)
```

Die Autos melden ihre Parkposition selbst an die VW-Cloud. Es ist also egal, wer gefahren ist.
Die Daten holt die Open-Source-Bibliothek [CarConnectivity](https://github.com/tillsteinbach/CarConnectivity).
Sie nutzt dieselbe (inoffizielle) Schnittstelle wie die Volkswagen App.

## Voraussetzungen

1. **Volkswagen App eingerichtet:** Jedes Auto ist einem VW-Konto als Hauptnutzer zugeordnet,
   und im Auto ist der Privatmodus aus. In der Volkswagen App muss die Parkposition zu sehen sein.
2. **Ein Rechner, der immer läuft:** z. B. ein Raspberry Pi, ein NAS mit Docker oder ein kleiner Server.
3. **Ein Google-Maps-API-Schlüssel** (siehe unten).

## 1. Google-Maps-API-Schlüssel anlegen

1. <https://console.cloud.google.com/> öffnen und ein Projekt anlegen, z. B. „Autofinder“.
2. Eine Zahlungsart hinterlegen. Google verlangt das, aber zwei Personen bleiben weit im kostenlosen Kontingent.
3. Unter **APIs & Dienste → Bibliothek** die **Maps JavaScript API** aktivieren.
4. Unter **APIs & Dienste → Anmeldedaten** einen **API-Schlüssel** erstellen.
5. Den Schlüssel einschränken:
   - API-Einschränkung: nur „Maps JavaScript API“
   - Website-Einschränkung: die Adresse, unter der ihr den Autofinder aufruft
6. Optional, zur Sicherheit: unter **Abrechnung → Budgets** ein Budget von 1 € mit Benachrichtigung anlegen.

## 2. Konfiguration

```bash
cd autofinder
cp config.example.json config.json
```

`config.json` ausfüllen. Diese Datei enthält Passwörter und wird **nicht** ins Git-Repo eingecheckt.

| Feld | Bedeutung |
|---|---|
| `google_maps_api_key` | Schlüssel aus Schritt 1 |
| `web_username`, `web_password` | Login für die Webseite, ein langes Passwort wählen |
| `vw_accounts` | Die VW-ID-Zugangsdaten. Sind beide Autos in einem Konto, reicht ein Eintrag. Sonst beide Konten eintragen. |
| `cars` | Optional: Anzeigename und Farbe pro Fahrgestellnummer (FIN, steht im Fahrzeugschein unter **E**) |
| `interval_seconds` | Wie oft die VW-Cloud abgefragt wird (mindestens 180, Standard 300) |

## 3. Starten

**Mit Docker (empfohlen, z. B. auf dem Raspberry Pi):**

```bash
docker compose up -d --build
docker compose logs -f      # prüfen, ob der VW-Login klappt
```

**Ohne Docker:**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Danach im Browser `http://<rechner-ip>:8080` öffnen und mit `web_username`/`web_password` anmelden.

## 4. Von unterwegs erreichbar machen

Am einfachsten und sichersten geht das mit **[Tailscale](https://tailscale.com/)** (kostenlos):

1. Tailscale auf dem Server und auf beiden Android-Handys installieren und mit demselben Konto anmelden.
2. Im Handy-Browser `http://<tailscale-name-des-servers>:8080` öffnen.

So muss kein Port am Router geöffnet werden.

## 5. Als App auf den Startbildschirm

In Chrome auf Android: Seite öffnen → Menü ⋮ → **„Zum Startbildschirm hinzufügen“**.
Danach startet der Autofinder wie eine eigene App.

## Gut zu wissen

- Die Position wird gemeldet, wenn das Auto abgestellt und verriegelt ist.
  In Tiefgaragen ohne Empfang kann sie fehlen oder veraltet sein. Wie alt sie ist, steht unter dem Autonamen.
- Die VW-Schnittstelle ist nicht offiziell. Ändert VW etwas, hilft meist ein Update von CarConnectivity:
  Versionen in `requirements.txt` erhöhen und `docker compose up -d --build` ausführen.
- Die Webseite ist eine eigene Karte mit Google Maps. Direkt in der Google-Maps-App können externe Daten
  nicht angezeigt werden, weil Google dafür keine Schnittstelle anbietet.

## Tests

```bash
.venv/bin/pip install pytest httpx
.venv/bin/python -m pytest tests
```

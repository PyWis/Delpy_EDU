# Guida al Deploy su PythonAnywhere (piano gratuito) — Modalità Demo

Questa guida descrive come pubblicare **Delpy EDU** su PythonAnywhere con l'account gratuito.  
L'app sarà raggiungibile all'indirizzo `https://TUOUSERNAME.pythonanywhere.com`.

---

## 1. Requisiti

- Account PythonAnywhere gratuito → [pythonanywhere.com](https://www.pythonanywhere.com)
- Nessuna carta di credito richiesta per il piano Beginner

Limitazioni del piano gratuito da tenere a mente:
- 1 sola web app
- CPU e traffico limitati
- Solo SQLite (nessun server MySQL esterno)
- Richieste HTTP uscenti limitate a host PythonAnywhere-whitelisted (l'invio di email tramite Brevo potrebbe non funzionare)

---

## 2. Caricare il codice

### Opzione A — Git (consigliata)

Apri una **Bash console** dal dashboard PythonAnywhere:

```bash
git clone https://github.com/TUO_UTENTE/Delpy_EDU.git
```

### Opzione B — Upload manuale

Dalla scheda **Files** carica l'archivio ZIP del progetto ed estrailo:

```bash
cd ~
unzip Delpy_EDU.zip
mv Delpy_EDU-main Delpy_EDU   # se il nome della cartella è diverso
```

---

## 3. Creare il virtualenv e installare le dipendenze

Nella **Bash console**:

```bash
mkvirtualenv --python=python3.10 delpyenv
cd ~/Delpy_EDU
pip install -r requirements.txt
```

> Se il virtualenv è già presente: `workon delpyenv`

---

## 4. Inizializzare il database e creare il superadmin demo

```bash
cd ~/Delpy_EDU
python app.py --run
```

Il comando:
1. Crea le tabelle del database (`delpy_edu.db`)
2. Crea automaticamente il superadmin demo con le credenziali:

```
Username : admin
Email    : admin@demo.local
Password : admin
```

> **Attenzione:** queste credenziali sono per uso demo/test.  
> Non usarle in un ambiente reale.

---

## 5. Configurare la Web App

1. Vai su **Web** nel menu PythonAnywhere
2. Clicca **Add a new web app**
3. Scegli **Manual configuration** (non "Flask")
4. Seleziona **Python 3.10**

### 5a. Virtualenv

Nel campo *Virtualenv* inserisci:

```
/home/TUOUSERNAME/.virtualenvs/delpyenv
```

### 5b. WSGI configuration file

Clicca sul link del file WSGI (es. `/var/www/TUOUSERNAME_pythonanywhere_com_wsgi.py`).  
Sostituisci **tutto** il contenuto con:

```python
import sys
import os

PROJECT_HOME = "/home/TUOUSERNAME/Delpy_EDU"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.chdir(PROJECT_HOME)

from app import create_app

application = create_app()
```

Sostituisci `TUOUSERNAME` con il tuo username PythonAnywhere, poi **salva**.

---

## 6. Variabili d'ambiente (opzionale)

Dalla scheda **Web → Environment variables** puoi aggiungere:

| Variabile | Valore |
|-----------|--------|
| `SECRET_KEY` | una stringa casuale lunga (es. generata con `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | `sqlite:////home/TUOUSERNAME/Delpy_EDU/delpy_edu.db` (percorso assoluto) |
| `BASE_URL` | `https://TUOUSERNAME.pythonanywhere.com` |

> Con il piano gratuito le chiamate Brevo (email) potrebbero essere bloccate.  
> Per la demo le funzioni email non sono indispensabili.

---

## 7. Reload e verifica

1. Clicca **Reload** nella scheda Web
2. Apri `https://TUOUSERNAME.pythonanywhere.com`
3. Accedi con:
   - **Email:** `admin@demo.local`
   - **Password:** `admin`

---

## 8. Ricaricare le modifiche al codice

Dopo ogni aggiornamento del codice:

```bash
cd ~/Delpy_EDU
git pull          # se usi Git
```

Poi clicca **Reload** nella scheda Web.

---

## 9. Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| `ModuleNotFoundError` | Verifica che il virtualenv sia corretto e che `pip install -r requirements.txt` sia andato a buon fine |
| Errore 500 | Controlla i log in **Web → Error log** |
| Database non trovato | Esegui di nuovo `python app.py --run` dalla Bash console |
| Pagina non aggiornata | Clicca **Reload** nella scheda Web |
| `OperationalError: no such table` | Il DB non è inizializzato — esegui `python app.py --run` |

---

## 10. Reset del database (opzionale)

Per cancellare tutti i dati e ricominciare da zero:

```bash
cd ~/Delpy_EDU
python app.py --reset
# digita RESET per confermare
python app.py --run   # ricrea le tabelle e il superadmin demo
```

Poi **Reload** dalla scheda Web.

# Database Pro - Gestione Avanzata

Un'applicazione desktop moderna e sicura per la gestione di database SQLite con crittografia integrata.

## Caratteristiche

- 🔐 **Crittografia integrata**: Database crittografati con Fernet (AES-128)
- 🛡️ **Autenticazione**: Protezione con password (PBKDF2-SHA256)
- 🎨 **Tema moderno**: Interfaccia elegante con temi scuri e chiari
- 📊 **Gestione completa**: Crea, modifica, elimina tabelle e record
- 📎 **Allegati**: Supporto per file allegati ai record
- ↩️ **Undo/Redo**: Sistema di undo/redo per le operazioni
- 📱 **Cross-platform**: Compatibile con Windows, macOS e Linux

## Prerequisiti

- Python 3.8+
- PyQt6
- cryptography
- Pillow

## Installazione

1. Clonare il repository:
```bash
git clone https://github.com/yourusername/DatabasePro.git
cd DatabasePro
```

2. Creare un ambiente virtuale:
```bash
python -m venv venv
```

3. Attivare l'ambiente virtuale:

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

4. Installare le dipendenze:
```bash
pip install -r requirements.txt
```

## Utilizzo

Avviare l'applicazione:
```bash
python app.py
```

### Primo accesso

- **Username**: Non richiesto
- **Password predefinita**: `Admin`
- **Azione consigliata**: Cambiare la password immediatamente

Dalla interfaccia puoi:
- Creare nuove tabelle con colonne personalizzate
- Aggiungere, modificare e eliminare record
- Allegare file ai record
- Cambiare il tema dell'interfaccia
- Proteggere il database con una password

## Sicurezza

### File sensibili

I seguenti file **NON devono essere mai** condivisi o pubblicati:

- `auth.json` - Credenziali di autenticazione
- `db_key.key` - Chiave di crittografia del database
- `database_avanzato.db.enc` - Database crittografato con dati sensibili

Questi file sono automaticamente aggiunti a `.gitignore`.

### Misure di sicurezza implementate

1. **Crittografia del database**: Fernet (AES-128 simmetrica)
2. **Hashing della password**: PBKDF2-SHA256 con 200.000 iterazioni
3. **Permessi file**: File sensibili con permessi ristretti (0o600)
4. **File nascosti**: Su Windows, file sensibili sono nascosti
5. **Scrittura atomica**: Operazioni JSON atomiche per evitare corruzione

## Compilazione dell'eseguibile

Per creare un eseguibile standalone:

```bash
python build_exe.py
```

L'eseguibile sarà creato nella cartella `dist/`.

**Nota**: L'eseguibile avrà i propri file di autenticazione e chiave di crittografia, indipendenti da quelli di sviluppo.

## Struttura del progetto

```
DatabasePro/
├── app.py                      # Applicazione principale
├── database.py                 # Gestione database e crittografia
├── auth.py                     # Autenticazione e hashing
├── config.py                   # Gestione tema e configurazione
├── dialogs.py                  # Dialog personalizzati
├── ui_components.py            # Componenti UI
├── ui_delegates.py             # Delegate per tabelle
├── validators.py               # Validatori per input
├── access.py                   # Controllo accesso
├── file_utils.py               # Utility per file
├── build_exe.py                # Script di build
├── requirements.txt            # Dipendenze
├── logo.png                    # Logo applicazione
├── app_config.json.example     # Esempio configurazione (da rinominare)
└── README.md                   # Questo file
```

## Variabili di ambiente (Opzionale)

Per usare variabili d'ambiente personalizzate, creare un file `.env`:

```
DATABASE_PATH=/path/to/database
AUTH_PATH=/path/to/auth
```

Non committare il file `.env` al repository.

## Contributi

Le pull request sono benvenute. Per cambiamenti importanti, aprire un issue prima per discussione.

## Licenza

MIT License

## Supporto

Per bug report, feature request o altre domande, aprire un [issue](https://github.com/yourusername/DatabasePro/issues).

---

**⚠️ IMPORTANTE**: 
- Non condividere mai i file `auth.json`, `db_key.key` o il database crittografato
- Cambiare la password predefinita al primo accesso
- Tenere il software aggiornato per ricevere patch di sicurezza

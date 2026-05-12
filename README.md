# 🏗️ Simetric Terrenos Bot

Bot que busca terrenos en CDMX cada 6 horas y te avisa por Telegram.

## Portales que revisa
- Inmuebles24
- Vivanuncios  
- Lamudi

## Filtros activos
- 400–1,500 m²
- Mínimo 14m de frente
- 14 colonias en CDMX

---

## Setup en 4 pasos

### 1. Crear bot de Telegram

1. Abre Telegram, busca **@BotFather**
2. Escribe `/newbot`
3. Dale nombre: `Simetric Terrenos Bot`
4. Guarda el **TOKEN** que te da (parece: `7123456789:AAFxxx...`)

### 2. Obtener tu Chat ID

1. Busca tu bot en Telegram y escribe `/start`
2. Entra a este URL en el navegador (pon tu token):
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
3. Busca `"chat":{"id":` — ese número es tu **CHAT_ID**

### 3. Deploy en Railway

1. Ve a [railway.app](https://railway.app) y crea cuenta
2. "New Project" → "Deploy from GitHub repo"
3. Sube este código a un repo de GitHub primero, luego conéctalo
4. En Railway, ve a **Variables** y agrega:
   ```
   TELEGRAM_TOKEN=7123456789:AAFxxx...
   TELEGRAM_CHAT_ID=123456789
   DB_PATH=/app/data/seen_listings.json
   ```
5. Railway detecta el Dockerfile y hace deploy automático

### 4. Verificar

Cuando inicie, recibirás en Telegram:
```
🤖 Simetric Terrenos Bot — Activo
```
Y al terminar el primer scan, un resumen.

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `TELEGRAM_TOKEN` | Token de @BotFather |
| `TELEGRAM_CHAT_ID` | Tu ID de chat |
| `DB_PATH` | Ruta del archivo de datos (default: `/app/data/seen_listings.json`) |

---

## Costo estimado en Railway
~$3–5 USD/mes en plan Hobby.

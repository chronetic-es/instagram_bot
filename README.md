# Gym DM Bot — Panel de Control para Instagram

Aplicación web (PWA) para automatizar respuestas a DMs de Instagram de un gimnasio con IA (OpenAI), con un panel de control para supervisar conversaciones, responder manualmente y recibir notificaciones push.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestor de Python)
- Node.js 18+
- PostgreSQL 15+

## Setup del Backend

```bash
cd backend

# Crear entorno virtual e instalar dependencias
uv sync

# Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Generar hash de contraseña
uv run python -c "import bcrypt; print(bcrypt.hashpw(b'tu_contraseña', bcrypt.gensalt()).decode())"
# Copiar el resultado en ADMIN_PASSWORD_HASH en .env

# Ejecutar migraciones
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/gym_dm_bot uv run alembic upgrade head

# Iniciar servidor
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Setup del Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Copiar y configurar variables de entorno
cp .env.example .env
# Añadir VITE_VAPID_PUBLIC_KEY

# Iniciar servidor de desarrollo
npm run dev

# Build para producción
npm run build
```

## Generar VAPID Keys

```bash
npx web-push generate-vapid-keys
```

Copiar `VAPID_PUBLIC_KEY` en `frontend/.env` y ambas en `backend/.env`.

## Configurar el Contenido del Gimnasio

Editar `backend/app/gym_context.txt` con la información real del gimnasio:
- Nombre y dirección
- Horarios
- Precios y membresías
- Clases disponibles
- Entrenadores

## Variables de Entorno del Backend (`.env`)

| Variable | Descripción |
|---|---|
| `META_VERIFY_TOKEN` | Token para verificar webhook de Meta |
| `META_PAGE_ACCESS_TOKEN` | Page Access Token de larga duración |
| `META_APP_SECRET` | App Secret para validar firma del webhook |
| `INSTAGRAM_ACCOUNT_ID` | IGSID de la cuenta del gimnasio |
| `OPENAI_API_KEY` | API key de OpenAI |
| `DATABASE_URL` | URL de conexión PostgreSQL |
| `VAPID_PUBLIC_KEY` | Clave pública VAPID |
| `VAPID_PRIVATE_KEY` | Clave privada VAPID |
| `VAPID_CLAIM_EMAIL` | Email para claims VAPID |
| `ADMIN_USERNAME` | Usuario del panel (default: admin) |
| `ADMIN_PASSWORD_HASH` | Hash bcrypt de la contraseña |
| `JWT_SECRET` | Secret para firmar JWT |
| `FRONTEND_URL` | URL del frontend (para CORS) |

## Configurar Webhook de Instagram

1. Exponer el backend públicamente (ngrok en desarrollo):
   ```bash
   ngrok http 8000
   ```

2. En Meta Developers, configurar el webhook:
   - URL: `https://tu-dominio.com/api/webhook/instagram`
   - Verify Token: el valor de `META_VERIFY_TOKEN`
   - Campos suscritos: `messages`

## Uso como PWA en iPhone

1. Abrir la URL de la app en Safari
2. Pulsar "Compartir" → "Añadir a pantalla de inicio"
3. Abrir la app desde el ícono en la pantalla de inicio
4. Activar notificaciones push desde el botón en el header

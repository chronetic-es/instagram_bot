import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select, text
from app.config import get_settings
from app.database import AsyncSessionLocal, engine
from app.models import Base, Setting
from app.deps import get_current_user
from app.routers import auth, webhook, conversations, settings, push, profiles
from app.services.websocket import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app_settings = get_settings()

app = FastAPI(title="Gym DM Bot", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[app_settings.frontend_url, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(webhook.router)
app.include_router(conversations.router)
app.include_router(settings.router)
app.include_router(push.router)
app.include_router(profiles.router)


@app.on_event("startup")
async def startup():
    # Seed default settings
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).where(Setting.key == "bot_enabled"))
        if not result.scalar_one_or_none():
            db.add(Setting(key="bot_enabled", value=True))
            await db.commit()
            logger.info("Seeded default settings: bot_enabled=true")
    from app.services.token_refresh import initialize_token, token_refresh_loop
    await initialize_token()
    asyncio.create_task(token_refresh_loop())
    logger.info("Application started")


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_policy():
    return """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Política de Privacidad</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem 4rem; color: #1a1a1a; line-height: 1.7; }
    h1 { font-size: 1.75rem; margin-bottom: 0.25rem; }
    h2 { font-size: 1.1rem; margin-top: 2rem; color: #333; }
    p, li { color: #444; }
    ul { padding-left: 1.5rem; }
    .updated { font-size: 0.85rem; color: #888; margin-bottom: 2rem; }
    a { color: #0066cc; }
  </style>
</head>
<body>
  <h1>Política de Privacidad</h1>
  <p class="updated">Última actualización: marzo 2026</p>
  <p>Esta política describe cómo el asistente virtual de mensajería de Instagram ("el Servicio") recopila, usa y protege la información de los usuarios que interactúan con nuestra cuenta de Instagram.</p>
  <h2>1. Información que recopilamos</h2>
  <ul>
    <li>Identificador de usuario de Instagram (IGSID) y nombre de usuario.</li>
    <li>Foto de perfil pública de Instagram.</li>
    <li>Contenido de los mensajes directos que nos envías.</li>
    <li>Fecha y hora de los mensajes.</li>
  </ul>
  <h2>2. Cómo usamos la información</h2>
  <p>La información se usa exclusivamente para responder preguntas sobre nuestros servicios y gestionar la comunicación entre el usuario y el equipo del gimnasio. Las respuestas automáticas son generadas por un modelo de inteligencia artificial (OpenAI) usando únicamente el historial de la conversación activa. No compartimos tus datos con terceros salvo lo necesario para proveer este servicio.</p>
  <h2>3. Almacenamiento y seguridad</h2>
  <p>Los mensajes se almacenan en una base de datos segura de uso exclusivo del gimnasio. Solo el propietario tiene acceso a las conversaciones. Los datos se conservan mientras sean necesarios para la atención al cliente y se eliminan a solicitud del usuario.</p>
  <h2>4. Tus derechos</h2>
  <ul>
    <li>Solicitar acceso a los datos que tenemos sobre ti.</li>
    <li>Solicitar la eliminación de tu historial de conversación.</li>
    <li>Dejar de interactuar con el servicio en cualquier momento.</li>
  </ul>
  <h2>5. Plataforma de Instagram</h2>
  <p>Este servicio utiliza la API de mensajería de Instagram (Meta). El uso de Instagram está sujeto a la <a href="https://privacycenter.instagram.com/policy" target="_blank" rel="noopener">Política de Privacidad de Instagram</a>.</p>
  <h2>6. Contacto</h2>
  <p>Para cualquier consulta sobre esta política, contáctanos por mensaje directo en Instagram o al correo electrónico indicado en nuestro perfil.</p>
</body>
</html>"""


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Validate JWT cookie before accepting
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        from app.deps import get_current_user
        from fastapi.security import APIKeyCookie
        from jose import jwt, JWTError
        payload = jwt.decode(
            token,
            app_settings.jwt_secret,
            algorithms=[app_settings.jwt_algorithm],
        )
        if not payload.get("sub"):
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; we only send from server
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        manager.disconnect(websocket)

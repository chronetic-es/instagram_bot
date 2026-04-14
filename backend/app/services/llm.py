import json
import logging
import os
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "notify_owner",
            "description": (
                "Envía una notificación push al entrenador cuando el usuario quiere "
                "hablar directamente con él o cuando hay una pregunta que no puedes responder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": (
                            "Breve razón de la notificación. "
                            "Ej: 'El usuario quiere hablar con el entrenador', "
                            "'Pregunta sobre precio que no puedo responder'"
                        ),
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "profile_complete",
            "description": (
                "Guarda el perfil del cliente cuando ya has recopilado de forma natural "
                "toda la información necesaria sobre su situación, historial, motivación, "
                "disponibilidad y compromiso económico."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "description": "Lista de preguntas y respuestas recopiladas a lo largo de la conversación.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "La pregunta tal como la formulaste en la conversación.",
                                },
                                "answer": {
                                    "type": "string",
                                    "description": "La respuesta que dio el usuario.",
                                },
                            },
                            "required": ["question", "answer"],
                        },
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "Resumen conciso del perfil en 2-3 frases: qué le motiva, "
                            "en qué punto está físicamente y cuánto compromiso tiene (incluyendo económico)."
                        ),
                    },
                },
                "required": ["answers", "summary"],
            },
        },
    },
]


def load_system_prompt() -> str:
    context_path = os.path.join(os.path.dirname(__file__), "..", "gym_context.txt")
    context_path = os.path.abspath(context_path)
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("gym_context.txt not found, using empty system prompt")
        return "Eres el asistente virtual de un entrenador personal. Responde en español."


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def _call_openai(messages: list, tools: list) -> object:
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
    )


async def process_message(
    conversation_history: list[dict],
    new_message: str,
    notify_callback,
    profile_callback=None,
) -> str:
    """
    Process a new message using OpenAI with function calling.

    conversation_history: list of dicts with keys 'direction', 'sender_type', 'content'
    new_message: the incoming user message text
    notify_callback: async callable(reason: str) to send push notification
    profile_callback: async callable(answers: list, summary: str) to save completed profile

    Returns the text response to send back to the user.
    """
    system_prompt = load_system_prompt()

    # Build OpenAI messages array from history (last 50 messages max)
    history = conversation_history[-50:] if len(conversation_history) > 50 else conversation_history

    openai_messages = [{"role": "system", "content": system_prompt}]

    for msg in history:
        if msg["direction"] == "inbound":
            openai_messages.append({"role": "user", "content": msg["content"]})
        else:
            # Both bot and owner outbound messages are treated as assistant
            openai_messages.append({"role": "assistant", "content": msg["content"]})

    openai_messages.append({"role": "user", "content": new_message})

    logger.info(f"Calling OpenAI with {len(openai_messages)} messages")

    try:
        response = await _call_openai(openai_messages, TOOLS)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "Lo siento, tuve un problema técnico. Por favor intenta de nuevo en un momento."

    choice = response.choices[0]

    # Handle tool calls
    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        tool_call = choice.message.tool_calls[0]

        if tool_call.function.name == "notify_owner":
            args = json.loads(tool_call.function.arguments)
            reason = args.get("reason", "El usuario requiere atención")
            logger.info(f"notify_owner called: {reason}")

            await notify_callback(reason)

            # Continue conversation with tool result
            openai_messages.append(choice.message)
            openai_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"status": "notified"}),
            })

            try:
                followup = await _call_openai(openai_messages, TOOLS)
                return followup.choices[0].message.content or "He avisado al entrenador. Pronto se pondrá en contacto contigo."
            except Exception as e:
                logger.error(f"OpenAI follow-up error: {e}")
                return "He avisado al entrenador. Pronto se pondrá en contacto contigo."

        if tool_call.function.name == "profile_complete":
            args = json.loads(tool_call.function.arguments)
            answers = args.get("answers", [])
            summary = args.get("summary", "")
            logger.info(f"profile_complete called. Summary: {summary[:80]}...")

            if profile_callback:
                await profile_callback(answers, summary)

            # Continue conversation to get the warm closing message
            openai_messages.append(choice.message)
            openai_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"status": "saved"}),
            })

            try:
                followup = await _call_openai(openai_messages, TOOLS)
                return followup.choices[0].message.content or "Perfecto, el entrenador se pondrá en contacto contigo pronto para hablar de tu situación y dar el siguiente paso."
            except Exception as e:
                logger.error(f"OpenAI follow-up error after profile_complete: {e}")
                return "Perfecto, el entrenador se pondrá en contacto contigo pronto para hablar de tu situación y dar el siguiente paso."

    return choice.message.content or "Lo siento, no pude generar una respuesta."

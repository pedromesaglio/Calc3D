"""
Manejadores de errores centralizados para la aplicación
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador personalizado de excepciones HTTP"""

    # Log del error
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} | "
        f"Path: {request.url.path} | "
        f"User: {request.session.get('user_id', 'anonymous')}"
    )

    # Detectar si es una request JSON o HTML
    accept = request.headers.get("accept", "")

    if "application/json" in accept:
        # Response JSON para APIs
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
            }
        )

    # Response HTML para navegador
    templates = request.app.state.templates

    # Mensajes user-friendly por código
    user_messages = {
        400: "Solicitud inválida. Por favor verifica los datos enviados.",
        401: "Debes iniciar sesión para acceder a esta página.",
        403: "No tienes permisos para acceder a este recurso.",
        404: "La página que buscas no existe.",
        429: "Has excedido el límite de solicitudes. Por favor espera un momento.",
        500: "Ocurrió un error en el servidor. Estamos trabajando para solucionarlo.",
        503: "El servicio no está disponible temporalmente. Intenta nuevamente en unos minutos.",
    }

    error_title = {
        400: "Solicitud Inválida",
        401: "Acceso Denegado",
        403: "Prohibido",
        404: "No Encontrado",
        429: "Demasiadas Solicitudes",
        500: "Error del Servidor",
        503: "Servicio No Disponible",
    }

    context = {
        "request": request,
        "status_code": exc.status_code,
        "error_title": error_title.get(exc.status_code, "Error"),
        "error_message": user_messages.get(exc.status_code, exc.detail),
        "technical_detail": exc.detail if exc.status_code >= 500 else None,
    }

    try:
        return templates.TemplateResponse(
            "error.html",
            context,
            status_code=exc.status_code
        )
    except Exception:
        # Si falla el template, retornar HTML simple
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error {exc.status_code}</title>
                <style>
                    body {{
                        font-family: system-ui, -apple-system, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                    }}
                    .error-card {{
                        background: white;
                        padding: 3rem;
                        border-radius: 1rem;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 500px;
                    }}
                    h1 {{ color: #667eea; margin: 0 0 1rem 0; }}
                    p {{ color: #64748b; }}
                    a {{
                        display: inline-block;
                        margin-top: 1.5rem;
                        padding: 0.75rem 1.5rem;
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        text-decoration: none;
                        border-radius: 0.5rem;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="error-card">
                    <h1>Error {exc.status_code}</h1>
                    <p>{user_messages.get(exc.status_code, exc.detail)}</p>
                    <a href="/">Volver al Inicio</a>
                </div>
            </body>
            </html>
            """,
            status_code=exc.status_code
        )


async def general_exception_handler(request: Request, exc: Exception):
    """Manejador de excepciones generales no capturadas"""

    # Log completo del error
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"User: {request.session.get('user_id', 'anonymous')}",
        exc_info=True  # Incluye stack trace
    )

    # En desarrollo, mostrar detalle del error
    from .config import Config
    show_details = not Config.IS_PRODUCTION

    accept = request.headers.get("accept", "")

    if "application/json" in accept:
        content = {
            "error": "Internal Server Error",
            "status_code": 500,
        }
        if show_details:
            content["detail"] = str(exc)
            content["type"] = type(exc).__name__

        return JSONResponse(
            status_code=500,
            content=content
        )

    # HTML Response
    context = {
        "request": request,
        "status_code": 500,
        "error_title": "Error del Servidor",
        "error_message": "Ocurrió un error inesperado. Estamos trabajando para solucionarlo.",
        "technical_detail": str(exc) if show_details else None,
    }

    templates = request.app.state.templates

    try:
        return templates.TemplateResponse(
            "error.html",
            context,
            status_code=500
        )
    except Exception:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error 500</title>
                <style>
                    body {{
                        font-family: system-ui, -apple-system, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                    }}
                    .error-card {{
                        background: white;
                        padding: 3rem;
                        border-radius: 1rem;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 500px;
                    }}
                    h1 {{ color: #667eea; margin: 0 0 1rem 0; }}
                    p {{ color: #64748b; }}
                    .detail {{ font-size: 0.875rem; color: #94a3b8; margin-top: 1rem; }}
                    a {{
                        display: inline-block;
                        margin-top: 1.5rem;
                        padding: 0.75rem 1.5rem;
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        text-decoration: none;
                        border-radius: 0.5rem;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="error-card">
                    <h1>Error 500</h1>
                    <p>Ocurrió un error inesperado en el servidor.</p>
                    {'<div class="detail">' + str(exc) + '</div>' if show_details else ''}
                    <a href="/">Volver al Inicio</a>
                </div>
            </body>
            </html>
            """,
            status_code=500
        )


def register_error_handlers(app):
    """Registra todos los manejadores de errores en la aplicación"""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    logger.info("Error handlers registered successfully")

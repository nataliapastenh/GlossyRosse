import io
import os
import re
import html
import base64
import random
import string
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, time

import bcrypt
import psycopg2
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL (RNF01 y RNF02)
# ---------------------------------------------------------
_base_dir_icono = os.path.dirname(os.path.abspath(__file__))
_logo_icono_candidatos = [
    os.path.join(_base_dir_icono, "logoglossy.png"),
    os.path.join(_base_dir_icono, "assets", "logoglossy.png"),
    os.path.join(_base_dir_icono, "assets", "galeria", "logoglossy.png"),
]
_icono_app = "✨"
for _ruta_logo_icono in _logo_icono_candidatos:
    if os.path.isfile(_ruta_logo_icono):
        _icono_app = Image.open(_ruta_logo_icono)
        break

st.set_page_config(
    page_title="Glossy Rosse · Belleza & Cuidado Personal",
    page_icon=_icono_app,
    layout="wide",
    initial_sidebar_state="collapsed"
)

DIRECCION_POR_DEFECTO = "Alberto Castex Taborga Poniente 1475"

if "vista_actual" not in st.session_state:
    st.session_state["vista_actual"] = "Inicio"

if "form_agenda_nonce" not in st.session_state:
    st.session_state["form_agenda_nonce"] = 0

if "ultima_reserva_ok" not in st.session_state:
    st.session_state["ultima_reserva_ok"] = None

VISTAS = {
    "Inicio": "Inicio",
    "Agendar": "Agendar hora",
    "Reserva": "Mi reserva",
    "Contacto": "Contacto",
    "Admin": "Acceso Martina",
}

esc = html.escape


def h(markup: str) -> str:
    """Compacta HTML multilínea para que Markdown no lo interprete como bloque de código."""
    return "".join(line.strip() for line in markup.strip().splitlines())


def clp(valor) -> str:
    """Formato de pesos chilenos: $25.000"""
    try:
        return "$" + f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def icono_servicio(nombre: str) -> str:
    n = (nombre or "").lower()
    mapa = [
        ("manicure", "💅"), ("uña", "💅"), ("pedicure", "🌸"), ("pedicura", "🌸"),
        ("pesta", "✨"), ("maquill", "💄"), ("facial", "🧖‍♀️"), ("limpieza", "🧖‍♀️"),
        ("ceja", "🪞"), ("cap", "💜"), ("peinado", "💜"),
    ]
    for clave, emoji in mapa:
        if clave in n:
            return emoji
    return "✨"


def _imagen_a_data_uri(ruta_archivo: str) -> str:
    ext = os.path.splitext(ruta_archivo)[1].lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(ruta_archivo, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{mime};base64,{b64}"


@st.cache_data
def obtener_logo_data_uri():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos_prioritarios = [
        os.path.join(base_dir, "logoglossy.png"),
        os.path.join(base_dir, "assets", "logoglossy.png"),
        os.path.join(base_dir, "assets", "galeria", "logoglossy.png"),
    ]
    for ruta in candidatos_prioritarios:
        if os.path.isfile(ruta):
            return _imagen_a_data_uri(ruta)

    carpetas = [
        base_dir,
        os.path.join(base_dir, "assets"),
        os.path.join(base_dir, "assets", "galeria"),
    ]
    for carpeta in carpetas:
        if os.path.isdir(carpeta):
            for fname in sorted(os.listdir(carpeta)):
                if "logo" in fname.lower() and fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return _imagen_a_data_uri(os.path.join(carpeta, fname))
    return None


# ---------------------------------------------------------
# ENVÍO DE CORREO DE CONFIRMACIÓN A CLIENTAS
# ---------------------------------------------------------
def enviar_correo_confirmacion(
    destinatario: str,
    nombre_clienta: str,
    codigo: str,
    servicio: str,
    horario: str,
    direccion_estudio: str,
):
    """
    Envía un correo de confirmación de reserva usando st.secrets["smtp"].
    Si no está configurado SMTP, devuelve (False, "no_configurado", detalle).
    """
    if "smtp" not in st.secrets:
        return (
            False,
            "no_configurado",
            "Agrega la sección [smtp] en .streamlit/secrets.toml para enviar correos reales automáticamente."
        )

    smtp_cfg = st.secrets["smtp"]
    host = smtp_cfg.get("host", "").strip()
    port = int(smtp_cfg.get("port", 587))
    user = smtp_cfg.get("user", "").strip()
    password = smtp_cfg.get("password", "")
    sender_name = smtp_cfg.get("sender_name", "Glossy Rosse · Coquimbo")

    if not host or not user or not password:
        return (
            False,
            "no_configurado",
            "Completa host, user y password en [smtp] dentro de .streamlit/secrets.toml."
        )

    msg = EmailMessage()
    msg["Subject"] = f"Confirmación de tu hora en Glossy Rosse · Código {codigo}"
    msg["From"] = f"{sender_name} <{user}>"
    msg["To"] = destinatario

    texto_plano = (
        f"Hola {nombre_clienta},\n\n"
        f"¡Tu hora en Glossy Rosse ha sido confirmada!\n\n"
        f"Código de reserva: {codigo}\n"
        f"Servicio: {servicio}\n"
        f"Fecha y hora: {horario}\n"
        f"Ubicación: {direccion_estudio}\n\n"
        f"Para consultar ubicación y datos de transferencia, ve a Mi reserva e ingresa tu código.\n"
        f"Recuerda que puedes modificar tu hora hasta 3 veces por reserva.\n\n"
        f"¡Te esperamos!\nGlossy Rosse"
    )

    msg.set_content(texto_plano)
    msg.add_alternative(f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1f1233; background: #fcfbff; padding: 24px;">
        <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e9defa; border-radius: 16px; padding: 24px;">
          <h2 style="color: #6b21a8; margin-top: 0;">Glossy Rosse · Belleza &amp; Cuidado Personal</h2>
          <p>Hola <strong>{esc(nombre_clienta)}</strong>, ¡tu cita ha sido confirmada!</p>
          <div style="background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 12px; padding: 16px; margin: 16px 0; text-align: center;">
            <div style="font-size: 12px; color: #6b5b82; text-transform: uppercase; letter-spacing: 1px;">Código de reserva</div>
            <div style="font-size: 26px; font-weight: 800; color: #2e1065; letter-spacing: 3px; margin-top: 4px;"><strong>{esc(codigo)}</strong></div>
          </div>
          <p><strong>Servicio:</strong> {esc(servicio)}</p>
          <p><strong>Fecha y hora:</strong> {esc(horario)}</p>
          <p><strong>Ubicación:</strong> {esc(direccion_estudio)}</p>
          <p style="font-size: 13px; color: #6b5b82; margin-top: 20px;">
            Para consultar ubicación y datos de transferencia, ingresa a <strong>Mi reserva</strong> con tu código.
          </p>
        </div>
      </body>
    </html>
    """, subtype="html")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
        return True, "enviado", f"Correo enviado a {destinatario}."
    except Exception as exc:
        return False, "error", f"No se pudo enviar el correo a {destinatario}: {exc}"


# ---------------------------------------------------------
# VALIDACIÓN DE DATOS DE CLIENTA (RUT Y TELÉFONO · MÁX. 9 CARACTERES)
# ---------------------------------------------------------
def validar_y_normalizar_rut(rut_raw: str):
    """
    Valida un RUT de hasta 9 caracteres (cuerpo numérico + dígito verificador 0-9 o K).
    Retorna (es_valido: bool, rut_normalizado_o_mensaje_error: str).
    """
    if not rut_raw or not rut_raw.strip():
        return False, "Por favor ingresa tu RUT (hasta 9 caracteres, ej: 123456789)."

    limpio = re.sub(r"[\.\-\s]", "", rut_raw.strip().upper())[:9]

    if not re.match(r"^\d{7,8}[0-9K]$", limpio):
        return (
            False,
            "Revisa tu RUT: ingresa hasta 9 caracteres (números y dígito verificador 0-9 o K). Ejemplo: 123456789."
        )

    cuerpo = limpio[:-1]
    dv_ingresado = limpio[-1]

    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = 11 - (suma % 11)
    if resto == 11:
        dv_esperado = "0"
    elif resto == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(resto)

    if dv_ingresado != dv_esperado:
        return (
            False,
            f"El dígito verificador de tu RUT no coincide (debería terminar en {dv_esperado}). Verifica los números e inténtalo de nuevo."
        )

    return True, f"{cuerpo}-{dv_ingresado}"


def validar_y_normalizar_telefono(telefono_raw: str):
    """
    Valida un número de teléfono de 9 dígitos (ej: 912345678 o 221234567).
    Retorna (es_valido: bool, telefono_normalizado_o_mensaje_error: str).
    """
    if not telefono_raw or not telefono_raw.strip():
        return False, "Por favor ingresa tu teléfono de 9 dígitos (ej: 912345678)."

    texto = telefono_raw.strip()
    if not re.match(r"^[\d\s\-]+$", texto):
        return False, "El teléfono solo puede contener números (ej: 912345678)."

    digitos = re.sub(r"\D", "", texto)[:9]

    if len(digitos) != 9:
        return (
            False,
            f"El teléfono debe tener 9 dígitos (actualmente tiene {len(digitos)}). Ejemplo: 912345678."
        )

    if not (digitos.startswith("9") or digitos.startswith("2")):
        return (
            False,
            "Ingresa un número de 9 dígitos que comience con 9 o con 2. Ejemplo: 912345678."
        )

    return True, digitos


def validar_datos_agenda(nombre: str, apellido: str, rut: str, correo: str, telefono: str):
    """Valida todos los campos del formulario de reserva con mensajes amigables."""
    if not nombre.strip() or len(nombre.strip()) < 2:
        return False, "Por favor escribe tu nombre (al menos 2 caracteres).", None, None

    if not apellido.strip() or len(apellido.strip()) < 2:
        return False, "Por favor escribe tu apellido (al menos 2 caracteres).", None, None

    rut_ok, rut_res = validar_y_normalizar_rut(rut)
    if not rut_ok:
        return False, rut_res, None, None

    tel_ok, tel_res = validar_y_normalizar_telefono(telefono)
    if not tel_ok:
        return False, tel_res, None, None

    correo_limpio = correo.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo_limpio):
        return False, "Por favor ingresa un correo electrónico válido (ejemplo: tunombre@correo.cl).", None, None

    return True, "", rut_res, tel_res


# ---------------------------------------------------------
# SISTEMA DE DISEÑO · PALETA MORADO / LILA + RESPONSIVIDAD
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --p-950: #2e1065;
    --p-900: #3b0764;
    --p-800: #581c87;
    --p-700: #6b21a8;
    --p-600: #7e22ce;
    --p-500: #9333ea;
    --p-400: #a855f7;
    --p-300: #c4b5fd;
    --p-200: #ddd6fe;
    --p-100: #ede9fe;
    --p-50:  #f5f3ff;
    --lilac-soft: #f3e8ff;
    --ink: #1f1233;
    --ink-soft: #6b5b82;
    --line: #e9defa;
    --radius: 18px;
    --shadow-sm: 0 2px 10px rgba(91, 33, 182, 0.06);
    --shadow-md: 0 12px 32px rgba(91, 33, 182, 0.10);
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.stApp {
    background:
        radial-gradient(1100px 500px at 100% -10%, #f3e8ff 0%, transparent 60%),
        radial-gradient(900px 500px at -10% 10%, #ede9fe 0%, transparent 55%),
        #fcfbff;
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: var(--ink);
}
.block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; max-width: 1180px; }
h1, h2, h3, h4 { font-family: 'Cormorant Garamond', serif; color: var(--ink); font-weight: 600; letter-spacing: -0.01em; font-style: normal !important; }
p, label, span, div { font-family: 'Plus Jakarta Sans', sans-serif; font-style: normal !important; }

/* Ocultar contadores de caracteres (ej. 0/9) */
[data-testid="InputInstructions"],
div[data-baseweb="input"] + div,
.stTextInput small {
    display: none !important;
}

.st-key-topnav {
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(10px);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.5rem 1rem;
    box-shadow: var(--shadow-sm);
    margin-bottom: 1.4rem;
}
.brand-box {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.65rem;
    width: 100%;
    padding: 0.1rem 0.25rem;
}
.brand-logo-img {
    height: 42px;
    width: 42px;
    flex: 0 0 42px;
    object-fit: cover;
    border-radius: 50%;
    border: 1.5px solid var(--p-300);
}
.brand-wordmark {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.65rem; font-weight: 700; line-height: 1.2;
    background: linear-gradient(90deg, var(--p-700), var(--p-400));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    white-space: nowrap;
}
.st-key-topnav .stButton > button {
    background: transparent !important; color: var(--p-800) !important;
    border: 1px solid transparent !important; box-shadow: none !important;
    font-weight: 600; font-size: 0.85rem; padding: 0.4rem 0.9rem;
}
.st-key-topnav .stButton > button:hover { background: var(--p-50) !important; color: var(--p-600) !important; }
.st-key-topnav .stButton > button[kind="primary"] {
    background: var(--p-100) !important; color: var(--p-700) !important; border-color: var(--p-200) !important;
}

.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    border-radius: 999px; font-weight: 600; font-size: 0.88rem;
    padding: 0.55rem 1.4rem; transition: all .2s ease;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--p-600), var(--p-500)) !important;
    color: #fff !important; border: none !important;
    box-shadow: 0 8px 20px rgba(126, 34, 206, 0.25);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 12px 26px rgba(126, 34, 206, 0.35);
}
.stButton > button[kind="secondary"] {
    background: #fff; color: var(--p-700); border: 1.5px solid var(--p-300);
}
.stButton > button[kind="secondary"]:hover { background: var(--p-50); border-color: var(--p-500); color: var(--p-800); }

.hero-lila {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 45%, #ddd6fe 100%);
    border: 1px solid var(--p-200); border-radius: 28px;
    padding: 3.4rem 2rem 2.8rem 2rem; text-align: center; margin-bottom: 1.2rem;
    box-shadow: var(--shadow-md);
}
.hero-lila::before, .hero-lila::after {
    content: ""; position: absolute; border-radius: 50%; filter: blur(2px); opacity: .55;
}
.hero-lila::before { width: 360px; height: 360px; right: -90px; top: -120px;
    background: radial-gradient(circle, #fff 0%, rgba(255,255,255,0) 70%); }
.hero-lila::after { width: 300px; height: 300px; left: -80px; bottom: -130px;
    background: radial-gradient(circle, #c4b5fd 0%, rgba(196,181,253,0) 70%); }
.hero-inner {
    position: relative; z-index: 2;
    display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
}
.hero-eyebrow {
    display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .22em; text-transform: uppercase;
    color: var(--p-700); background: rgba(255,255,255,.7); border: 1px solid var(--p-200);
    padding: .4rem 1rem; border-radius: 999px; margin-bottom: 1.1rem;
}
.hero-title {
    font-family: 'Cormorant Garamond', serif !important; font-size: 3.6rem !important; font-weight: 700 !important;
    color: var(--p-950) !important; line-height: 1.08; width: 100%; max-width: 780px; margin: 0 auto .9rem auto !important;
    font-style: normal !important; text-align: center !important;
}
.hero-subtitle {
    display: block; width: 100%; font-size: 1rem; color: #5b4a73; max-width: 660px; margin: 0 auto 1.6rem auto;
    line-height: 1.65; text-align: center !important; font-style: normal !important;
}
.hero-badges { display: flex; flex-wrap: wrap; gap: .6rem; justify-content: center; }
.hero-badge {
    font-size: .78rem; font-weight: 600; color: var(--p-800);
    background: rgba(255,255,255,.75); border: 1px solid var(--p-200);
    padding: .4rem .9rem; border-radius: 999px;
}

.section-eyebrow {
    text-align: center; font-size: .72rem; font-weight: 700; letter-spacing: .2em;
    text-transform: uppercase; color: var(--p-500); margin: 2.2rem 0 .3rem 0;
}
.section-heading {
    text-align: center; font-family: 'Cormorant Garamond', serif !important;
    font-size: 2.4rem !important; color: var(--p-950) !important; margin: 0 0 .4rem 0 !important;
}
.section-sub { text-align: center; color: var(--ink-soft); font-size: .93rem; max-width: 540px; margin: 0 auto 1.4rem auto; }
.page-head { margin-top: .4rem; }

.service-item-card {
    display: flex; align-items: center; flex-wrap: wrap; gap: 0.9rem;
    background: #fff; border: 1px solid var(--line); border-radius: 16px;
    padding: 1rem 1.2rem; margin-bottom: .75rem; box-shadow: var(--shadow-sm);
    transition: all .2s ease;
}
.service-item-card:hover { border-color: var(--p-300); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.service-icon {
    flex: 0 0 46px; height: 46px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--p-100), var(--lilac-soft)); font-size: 1.3rem;
}
.service-body { flex: 1 1 220px; min-width: 0; }
.service-name { font-weight: 700; font-size: .98rem; color: var(--ink); overflow-wrap: anywhere; word-break: break-word; }
.service-desc { font-size: .82rem; color: var(--ink-soft); margin-top: .2rem; line-height: 1.45; overflow-wrap: anywhere; word-break: break-word; }

.service-grid-card {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.15rem 1rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-sm);
    text-align: center;
    height: 100%;
    transition: all .2s ease;
}
.service-grid-card:hover {
    border-color: var(--p-300);
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
}
.service-grid-icon {
    width: 48px;
    height: 48px;
    margin: 0 auto 0.65rem auto;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--p-100), var(--lilac-soft));
    font-size: 1.35rem;
}
.service-grid-name {
    font-weight: 700;
    font-size: 0.96rem;
    color: var(--ink);
    margin-bottom: 0.25rem;
}
.service-grid-meta {
    font-size: 0.8rem;
    color: var(--ink-soft);
    margin-bottom: 0.65rem;
}
.service-grid-price {
    display: inline-block;
    font-weight: 800;
    font-size: 0.9rem;
    color: var(--p-700);
    background: var(--p-50);
    border: 1px solid var(--p-200);
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
}

.soft-panel {
    background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
    padding: 1.5rem 1.6rem; margin-bottom: 1rem; box-shadow: var(--shadow-sm);
}
.soft-panel h3 { margin-top: 0; font-size: 1.5rem; color: var(--p-900); }
.soft-panel p { color: #4a3b61; font-size: .92rem; line-height: 1.6; margin: .45rem 0; }
.panel-lila { background: linear-gradient(160deg, #faf5ff, #f3e8ff); border-color: var(--p-200); }

.reserva-banner-ok {
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border: 1.5px solid var(--p-300);
    border-radius: var(--radius);
    padding: 1.3rem 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: var(--shadow-sm);
}
.reserva-codigo-grande {
    display: inline-block;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1.65rem;
    font-weight: 900;
    letter-spacing: .14em;
    color: var(--p-950);
    background: #ffffff;
    border: 2px solid var(--p-400);
    padding: .35rem 1rem;
    border-radius: 12px;
    margin: .35rem 0;
}

.step-card {
    background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
    padding: 1.5rem 1.3rem; text-align: center; box-shadow: var(--shadow-sm); height: 100%;
}
.step-num {
    width: 42px; height: 42px; margin: 0 auto .8rem auto; border-radius: 50%;
    background: linear-gradient(135deg, var(--p-600), var(--p-400)); color: #fff;
    font-weight: 800; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 18px rgba(126,34,206,.28);
}
.step-title { font-weight: 700; color: var(--p-900); margin-bottom: .3rem; }
.step-text { font-size: .85rem; color: var(--ink-soft); line-height: 1.55; }

.badge { display: inline-block; font-size: .72rem; font-weight: 700; padding: .22rem .7rem; border-radius: 999px; max-width: 100%; }
.badge-ok { background: #ede9fe; color: #5b21b6; }
.badge-mod { background: #fae8ff; color: #86198f; }
.badge-cancel { background: #f1f1f4; color: #6b7280; }
.badge-warn { background: #fef3c7; color: #92400e; }

.code-chip {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-weight: 900;
    font-size: 1.25rem;
    letter-spacing: .12em;
    background: var(--p-100);
    color: var(--p-950);
    border: 1.5px solid var(--p-300);
    padding: .28rem .8rem;
    border-radius: 10px;
}
.code-chip-sm {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-weight: 800;
    font-size: .92rem;
    letter-spacing: .08em;
    background: var(--p-100);
    color: var(--p-900);
    padding: .15rem .55rem;
    border-radius: 8px;
}

.info-row { display: flex; justify-content: space-between; padding: .55rem 0; border-bottom: 1px dashed var(--line); font-size: .92rem; gap: .75rem; }
.info-row:last-child { border-bottom: none; }
.info-row span:first-child { color: var(--ink-soft); }
.info-row span:last-child { font-weight: 600; color: var(--ink); text-align: right; }

.cal-day-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 0.95rem 1rem;
    box-shadow: var(--shadow-sm);
    height: 100%;
    margin-bottom: 0.75rem;
}
.cal-day-header {
    font-weight: 700;
    color: var(--p-900);
    font-size: 0.92rem;
    border-bottom: 1px solid var(--p-100);
    padding-bottom: 0.45rem;
    margin-bottom: 0.55rem;
}
.cal-slot-free {
    background: #f5f3ff;
    border: 1px solid #ddd6fe;
    color: #5b21b6;
    border-radius: 10px;
    padding: 0.35rem 0.55rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.35rem;
}
.cal-slot-busy {
    background: #fae8ff;
    border: 1px solid #e879f9;
    color: #701a75;
    border-radius: 10px;
    padding: 0.35rem 0.55rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.35rem;
}

[data-testid="stForm"] {
    background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
    padding: 1.6rem 1.6rem 1.2rem 1.6rem; box-shadow: var(--shadow-sm);
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
[data-baseweb="select"] > div {
    border-radius: 12px !important; border-color: var(--p-200) !important; background: #fdfcff !important;
}
.stTextInput input:focus, .stNumberInput input:focus { border-color: var(--p-500) !important; box-shadow: 0 0 0 3px rgba(147,51,234,.15) !important; }
label p { font-weight: 600 !important; color: var(--p-900) !important; font-size: .85rem !important; }

.stTabs [data-baseweb="tab-list"] { gap: .4rem; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] { border-radius: 12px 12px 0 0; padding: .7rem 1.1rem; font-weight: 600; color: var(--ink-soft); }
.stTabs [aria-selected="true"] { color: var(--p-700) !important; background: var(--p-50); }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--p-500) !important; }

[data-testid="stMetric"] {
    background: #fff; border: 1px solid var(--line); border-radius: 16px;
    padding: 1.1rem 1.3rem; box-shadow: var(--shadow-sm);
}
[data-testid="stMetricValue"] { color: var(--p-700); font-family: 'Cormorant Garamond', serif; font-weight: 700; }
[data-testid="stSidebar"] { background: #faf7ff; border-right: 1px solid var(--line); }
[data-testid="stAlert"] { border-radius: 14px; }

.site-footer {
    margin-top: 3rem; padding: 1.6rem 1rem; text-align: center; border-top: 1px solid var(--line);
    color: var(--ink-soft); font-size: .82rem;
}
.site-footer strong { color: var(--p-700); font-family: 'Cormorant Garamond', serif; font-size: 1.15rem; }

@media (max-width: 768px) {
    .block-container {
        padding-top: 0.85rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-bottom: 2.2rem !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.65rem !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .st-key-topnav {
        border-radius: 22px;
        padding: 0.65rem 0.8rem;
    }
    .brand-box {
        justify-content: center;
        align-items: center;
        width: 100%;
        padding-left: 0;
    }
    .brand-wordmark {
        font-size: 1.5rem;
    }
    .hero-title { font-size: 2.2rem !important; }
    .hero-subtitle { font-size: 0.94rem; text-align: center !important; }
    .hero-lila { padding: 2.4rem 1.1rem 2rem 1.1rem; border-radius: 20px; }
    .section-heading { font-size: 1.85rem !important; }
    .soft-panel, [data-testid="stForm"], .reserva-banner-ok {
        padding: 1.1rem 1rem !important;
    }
    .service-item-card {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.65rem;
    }
    .reserva-codigo-grande {
        font-size: 1.25rem;
        letter-spacing: .08em;
    }
    input, textarea, select {
        font-size: 16px !important;
    }
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# CONEXIÓN A SUPABASE (POSTGRESQL) CON RECUPERACIÓN AUTOMÁTICA
# ---------------------------------------------------------
@st.cache_resource
def init_connection():
    pg = st.secrets["postgres"]
    nombre_bd = pg.get("database") or pg.get("dbname") or "postgres"
    return psycopg2.connect(
        host=pg["host"],
        database=nombre_bd,
        user=pg["user"],
        password=pg["password"],
        port=int(pg.get("port", 5432)),
        sslmode=pg.get("sslmode", "require")
    )


try:
    conn = init_connection()
except Exception as e:
    st.error(f"No fue posible conectar con el sistema en este momento: {e}")
    st.stop()


def get_healthy_connection():
    """Garantiza que la conexión esté abierta y sin transacciones abortadas."""
    global conn
    if conn is None or conn.closed != 0:
        st.cache_resource.clear()
        conn = init_connection()
    if conn.status != psycopg2.extensions.STATUS_READY:
        try:
            conn.rollback()
        except Exception:
            st.cache_resource.clear()
            conn = init_connection()
    return conn


def run_query(query, parameters=(), fetch=True):
    """Ejecuta una consulta SQL con rollback automático ante cualquier error."""
    active_conn = get_healthy_connection()
    try:
        with active_conn.cursor() as cursor:
            cursor.execute(query, parameters)
            active_conn.commit()
            if fetch:
                return cursor.fetchall()
    except Exception:
        try:
            active_conn.rollback()
        except Exception:
            pass
        raise


def asegurar_columna_ubicacion():
    """Agrega ubicacion_estudio a administradores si aún no existe."""
    try:
        run_query(
            "ALTER TABLE administradores ADD COLUMN IF NOT EXISTS ubicacion_estudio TEXT;",
            fetch=False
        )
    except Exception:
        pass


asegurar_columna_ubicacion()


def obtener_ubicacion_estudio() -> str:
    """Devuelve la ubicación configurada en la base de datos o la dirección por defecto."""
    try:
        rows = run_query("""
            SELECT ubicacion_estudio
            FROM administradores
            WHERE ubicacion_estudio IS NOT NULL AND TRIM(ubicacion_estudio) <> ''
            ORDER BY id ASC
            LIMIT 1
        """)
        if rows and rows[0][0]:
            return str(rows[0][0]).strip()
    except Exception:
        pass
    return DIRECCION_POR_DEFECTO


def generar_codigo_reserva():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def bloque_tiene_reserva_activa(disponibilidad_id):
    """Verifica si un bloque horario tiene reservas Confirmadas o Modificadas (RF16)."""
    res = run_query("""
        SELECT COUNT(*) FROM reservas 
        WHERE disponibilidad_id = %s AND estado IN ('Confirmada', 'Modificada')
    """, (disponibilidad_id,))
    return res[0][0] > 0


def badge_estado(estado):
    clase = {"Confirmada": "badge-ok", "Modificada": "badge-mod", "Cancelada": "badge-cancel"}.get(estado, "badge-ok")
    return f'<span class="badge {clase}">{esc(str(estado))}</span>'


def encabezado(eyebrow, titulo, subtitulo=""):
    sub = f'<p class="section-sub">{esc(subtitulo)}</p>' if subtitulo else ""
    st.markdown(h(f"""
        <div class="page-head">
            <div class="section-eyebrow">{esc(eyebrow)}</div>
            <h2 class="section-heading">{titulo}</h2>
            {sub}
        </div>
    """), unsafe_allow_html=True)


# ---------------------------------------------------------
# IMÁGENES EMBEBIDAS EN EL MISMO CÓDIGO + CARRUSEL VERTICAL
# ---------------------------------------------------------
SLIDE_SPECS = [
    ("IMG_2748.jpeg", "Pestañas y Diseño de Cejas", "Armonía y prolijidad en cada detalle", (245, 243, 255), (126, 34, 206)),
    ("IMG_3530.jpeg", "Lashes By Martina", "Atención personalizada · @glossyrosse_", (250, 232, 255), (134, 25, 143)),
    ("IMG_3672.jpeg", "Lashes By Martina · Studio", "Resultado duradero en Coquimbo", (250, 245, 255), (107, 33, 168)),
    ("IMG_5502.jpg", "Manicure Almendrada Rosa", "Acabado suave y elegante", (243, 232, 255), (107, 33, 168)),
    ("IMG_3765.jpg", "French Pastel & Brillos", "Detalle delicado en tonos claros", (237, 233, 254), (91, 33, 182)),
    ("IMG_5535.jpg", "Extensiones de Pestañas", "Mirada definida y natural", (233, 213, 255), (59, 7, 100)),
    ("IMG_4972.jpg", "Manicure Efecto Perlado", "Reflejos nacarados en lila y rosa", (237, 233, 254), (107, 33, 168)),
    ("IMG_5435.jpg", "Pedicura & Esmaltado", "Cuidado completo para tus pies", (243, 232, 255), (126, 34, 206)),
    ("IMG_4914.jpg", "Manicure Clásico", "Brillo intenso y terminación impecable", (233, 213, 255), (88, 28, 135)),
    ("IMG_5923.jpg", "Maquillaje & Peinado", "Look luminoso para ocasiones especiales", (245, 243, 255), (76, 29, 149)),
]


def _fuente(size):
    for ruta in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(ruta, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _crear_imagen_base64_embebida(titulo, subtitulo, bg_rgb, accent_rgb):
    w, hgt = 640, 860
    img = Image.new("RGB", (w, hgt), bg_rgb)
    draw = ImageDraw.Draw(img)

    draw.ellipse([280, -90, 720, 350], fill=(255, 255, 255))
    draw.ellipse([-120, 520, 360, 980], fill=(255, 255, 255))
    draw.rounded_rectangle([24, 24, w - 24, hgt - 24], radius=26, outline=accent_rgb, width=3)

    draw.rounded_rectangle([54, 64, 286, 108], radius=22, fill=accent_rgb)
    draw.text((78, 76), "GLOSSY ROSSE", fill=(255, 255, 255), font=_fuente(20))

    draw.text((54, 290), titulo, fill=accent_rgb, font=_fuente(36))
    draw.text((54, 350), subtitulo, fill=(60, 40, 85), font=_fuente(22))
    draw.text((54, 750), "Estética & Cosmetología · Coquimbo", fill=(107, 94, 130), font=_fuente(19))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


@st.cache_data
def construir_slides_en_codigo():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    carpeta_local = os.path.join(base_dir, "assets", "galeria")
    slides = []
    vistos = set()

    for filename, titulo, subtitulo, bg_rgb, accent_rgb in SLIDE_SPECS:
        ruta_real = os.path.join(carpeta_local, filename)
        if os.path.isfile(ruta_real):
            src = _imagen_a_data_uri(ruta_real)
            vistos.add(filename.lower())
            slides.append({"src": src, "title": titulo, "subtitle": subtitulo})

    if not slides:
        for filename, titulo, subtitulo, bg_rgb, accent_rgb in SLIDE_SPECS:
            slides.append({
                "src": _crear_imagen_base64_embebida(titulo, subtitulo, bg_rgb, accent_rgb),
                "title": titulo,
                "subtitle": subtitulo,
            })
    elif os.path.isdir(carpeta_local):
        for fname in sorted(os.listdir(carpeta_local)):
            if (
                fname.lower() not in vistos
                and "logo" not in fname.lower()
                and fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ):
                ruta_extra = os.path.join(carpeta_local, fname)
                slides.append({
                    "src": _imagen_a_data_uri(ruta_extra),
                    "title": "Glossy Rosse",
                    "subtitle": "Atención personalizada · Coquimbo",
                })

    return slides


def render_carrusel_uno_a_uno(slides, intervalo_ms=3400):
    slides_js = "[" + ",".join(
        f'{{src:"{s["src"]}",title:"{s["title"]}",subtitle:"{s["subtitle"]}"}}'
        for s in slides
    ) + "]"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }}
        body {{ background: transparent; display: flex; justify-content: center; }}
        .stage {{
            position: relative; width: 100%; max-width: 440px; height: 620px; border-radius: 24px; overflow: hidden;
            border: 1px solid #e9defa; box-shadow: 0 14px 34px rgba(91, 33, 182, 0.14); background: #f3e8ff;
        }}
        .stage img {{ width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; transition: opacity 0.4s ease; }}
        .caption-overlay {{
            position: absolute; left: 0; right: 0; bottom: 0; padding: 2.8rem 1.4rem 1.15rem 1.4rem; color: #fff;
            background: linear-gradient(to top, rgba(46, 16, 101, 0.88), rgba(46, 16, 101, 0.35), transparent);
        }}
        .caption-overlay h4 {{ font-family: 'Cormorant Garamond', serif; font-size: 1.65rem; font-weight: 700; margin-bottom: 2px; font-style: normal; }}
        .caption-overlay p {{ font-size: 0.85rem; color: #ede9fe; font-style: normal; }}
        .arrow-btn {{
            position: absolute; top: 50%; transform: translateY(-50%); width: 40px; height: 40px; border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.6); background: rgba(255,255,255,0.22); backdrop-filter: blur(6px);
            color: #fff; font-size: 1.35rem; cursor: pointer; transition: background .2s;
        }}
        .arrow-btn:hover {{ background: rgba(126, 34, 206, 0.85); }}
        .prev {{ left: 12px; }} .next {{ right: 12px; }}
        .counter {{
            position: absolute; top: 14px; left: 14px; font-size: .74rem; font-weight: 600; color: #fff;
            background: rgba(46, 16, 101, 0.48); padding: 4px 11px; border-radius: 999px;
        }}
        .dots-row {{
            position: absolute; top: 14px; right: 14px; display: flex; gap: 5px;
            background: rgba(46, 16, 101, 0.42); padding: 6px 10px; border-radius: 999px;
        }}
        .dot-btn {{ width: 7px; height: 7px; border-radius: 50%; border: none; background: rgba(255,255,255,0.5); cursor: pointer; transition: all .25s; }}
        .dot-btn.active {{ width: 18px; border-radius: 999px; background: #d8b4fe; }}
        @media (max-width: 768px) {{
            .stage {{ max-width: 390px; height: 520px; border-radius: 20px; }}
            .caption-overlay h4 {{ font-size: 1.35rem; }}
        }}
    </style>
    </head>
    <body>
        <div class="stage" id="glossyStage">
            <img id="glossyImg" src="" alt="Galería Glossy Rosse" />
            <div class="counter" id="glossyCounter"></div>
            <div class="dots-row" id="glossyDots"></div>
            <button class="arrow-btn prev" onclick="prevImg()" aria-label="Anterior">‹</button>
            <button class="arrow-btn next" onclick="nextImg()" aria-label="Siguiente">›</button>
            <div class="caption-overlay">
                <h4 id="glossyTitle"></h4>
                <p id="glossySub"></p>
            </div>
        </div>
        <script>
            const items = {slides_js};
            let current = 0;
            let intervalId = null;

            const imgNode = document.getElementById("glossyImg");
            const titleNode = document.getElementById("glossyTitle");
            const subNode = document.getElementById("glossySub");
            const dotsNode = document.getElementById("glossyDots");
            const counterNode = document.getElementById("glossyCounter");
            const stageNode = document.getElementById("glossyStage");

            function paintDots() {{
                dotsNode.innerHTML = "";
                items.forEach((_, i) => {{
                    const btn = document.createElement("button");
                    btn.className = "dot-btn" + (i === current ? " active" : "");
                    btn.onclick = () => {{ showSlide(i); restartTimer(); }};
                    dotsNode.appendChild(btn);
                }});
            }}

            function showSlide(target) {{
                current = (target + items.length) % items.length;
                imgNode.style.opacity = 0.25;
                setTimeout(() => {{
                    imgNode.src = items[current].src;
                    titleNode.textContent = items[current].title;
                    subNode.textContent = items[current].subtitle;
                    counterNode.textContent = (current + 1) + " / " + items.length;
                    imgNode.style.opacity = 1;
                    paintDots();
                }}, 150);
            }}

            function nextImg() {{ showSlide(current + 1); restartTimer(); }}
            function prevImg() {{ showSlide(current - 1); restartTimer(); }}

            function restartTimer() {{
                if (intervalId) clearInterval(intervalId);
                intervalId = setInterval(() => showSlide(current + 1), {intervalo_ms});
            }}

            stageNode.addEventListener("mouseenter", () => clearInterval(intervalId));
            stageNode.addEventListener("mouseleave", restartTimer);

            showSlide(0);
            restartTimer();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=640)


# ---------------------------------------------------------
# NAVEGACIÓN SUPERIOR CON LOGO + BARRA LATERAL
# ---------------------------------------------------------
def ir_a(vista_nueva):
    st.session_state["vista_actual"] = vista_nueva


logo_uri = obtener_logo_data_uri()
logo_html = f'<img class="brand-logo-img" src="{logo_uri}" alt="Logo Glossy Rosse" />' if logo_uri else ""

with st.container(key="topnav"):
    nav_logo, nav_1, nav_2, nav_3, nav_4, nav_5 = st.columns([2.4, 1, 1.15, 1.15, 1, 1.5], vertical_alignment="center")
    with nav_logo:
        st.markdown(h(f"""
            <div class="brand-box">
                {logo_html}
                <div class="brand-wordmark">Glossy Rosse</div>
            </div>
        """), unsafe_allow_html=True)
    for col, (clave, etiqueta) in zip([nav_1, nav_2, nav_3, nav_4, nav_5], VISTAS.items()):
        with col:
            activo = st.session_state["vista_actual"] == clave
            st.button(
                etiqueta, key=f"top_{clave}", use_container_width=True,
                type="primary" if activo else "secondary",
                on_click=ir_a, args=(clave,)
            )

with st.sidebar:
    if logo_uri:
        st.image(logo_uri, width=84)
    st.markdown("### Glossy Rosse")
    st.caption("Belleza & Cuidado Personal · Coquimbo")
    st.markdown("---")
    claves = list(VISTAS.keys())
    vista_sidebar = st.radio(
        "Secciones", claves,
        index=claves.index(st.session_state["vista_actual"]),
        format_func=lambda k: VISTAS[k]
    )
    if vista_sidebar != st.session_state["vista_actual"]:
        st.session_state["vista_actual"] = vista_sidebar
        st.rerun()

vista = st.session_state["vista_actual"]
ubicacion_actual = obtener_ubicacion_estudio()


# ---------------------------------------------------------
# VISTA 1: INICIO (PRIMERO CAJA "REALZA TU BRILLO NATURAL" Y ABAJO CARRUSEL)
# ---------------------------------------------------------
if vista == "Inicio":
    st.markdown(h("""
        <div class="hero-lila">
            <div class="hero-inner">
                <div class="hero-eyebrow">Belleza &amp; Cuidado Personal</div>
                <h1 class="hero-title">Realza tu brillo natural</h1>
                <p class="hero-subtitle">
                    Maquillaje, limpiezas faciales, manicure, pedicura, extensiones de pestañas y tratamientos capilares, con atención personalizada.
                </p>
                <div class="hero-badges">
                    <span class="hero-badge">✨ Atención personalizada</span>
                    <span class="hero-badge">📅 Reserva online en minutos</span>
                    <span class="hero-badge">🔁 Cambios de hora flexibles</span>
                </div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    _, col_btn_center, _ = st.columns([3.5, 2, 3.5])
    with col_btn_center:
        st.button("Agendar mi hora", key="hero_cta_btn", type="primary",
                  use_container_width=True, on_click=ir_a, args=("Agendar",))

    encabezado("Galería", "Nuestro trabajo",
               "Mira algunos de nuestros resultados en el estudio.")

    render_carrusel_uno_a_uno(construir_slides_en_codigo(), intervalo_ms=3400)

    encabezado("Servicios", "Elige tu próxima cita",
               "Todos nuestros servicios disponibles con duración y valor referencial.")

    servicios = run_query("SELECT nombre, precio, duracion_minutos FROM servicios ORDER BY id ASC")
    if servicios:
        for i in range(0, len(servicios), 4):
            fila_servs = servicios[i:i + 4]
            cols_4 = st.columns(4, gap="medium")
            for idx_col in range(4):
                with cols_4[idx_col]:
                    if idx_col < len(fila_servs):
                        serv = fila_servs[idx_col]
                        st.markdown(h(f"""
                            <div class="service-grid-card">
                                <div class="service-grid-icon">{icono_servicio(serv[0])}</div>
                                <div class="service-grid-name">{esc(str(serv[0]))}</div>
                                <div class="service-grid-meta">⏱ {serv[2]} min</div>
                                <div class="service-grid-price">{clp(serv[1])} CLP</div>
                            </div>
                        """), unsafe_allow_html=True)
    else:
        st.info("Aún no hay servicios registrados.")

    encabezado("Cómo funciona", "Agenda en tres simples pasos")
    p1, p2, p3 = st.columns(3, gap="large")
    pasos = [
        ("1", "Elige tu servicio", "Selecciona el tratamiento y el horario disponible que prefieras."),
        ("2", "Recibe tu código", "Al confirmar obtienes un código único de 6 caracteres. Guárdalo."),
        ("3", "Gestiona tu hora", "Con tu código puedes consultar ubicación, datos de transferencia o cambiar tu hora."),
    ]
    for col, (num, tit, txt) in zip([p1, p2, p3], pasos):
        with col:
            st.markdown(h(f"""
                <div class="step-card">
                    <div class="step-num">{num}</div>
                    <div class="step-title">{tit}</div>
                    <div class="step-text">{txt}</div>
                </div>
            """), unsafe_allow_html=True)


# ---------------------------------------------------------
# VISTA 2: AGENDAR HORA
# ---------------------------------------------------------
elif vista == "Agendar":
    encabezado("Reservas", "Agenda tu hora", "Completa tus datos y elige el horario que más te acomode.")

    if st.session_state.get("ultima_reserva_ok"):
        info_ok = st.session_state.pop("ultima_reserva_ok")
        st.markdown(h(f"""
            <div class="reserva-banner-ok">
                <div style="font-weight:700; color:#3b0764; font-size:1.05rem;">
                    ✅ ¡Reserva confirmada con éxito para {esc(info_ok['nombre'])}!
                </div>
                <div style="color:#5b4a73; font-size:0.88rem; margin-top:.2rem;">
                    Tu código de reserva es:
                </div>
                <div class="reserva-codigo-grande"><strong>{esc(info_ok['codigo'])}</strong></div>
                <div style="color:#4a3b61; font-size:0.88rem; margin-top:.35rem;">
                    <strong>Servicio:</strong> {esc(info_ok['servicio'])} · <strong>Horario:</strong> {esc(info_ok['horario'])}<br>
                    <strong>Ubicación:</strong> {esc(info_ok['ubicacion'])}
                </div>
                <div style="color:#3b0764; font-size:0.86rem; margin-top:.45rem; background:#ffffff; padding:.6rem .8rem; border-radius:10px; border:1px solid #ddd6fe;">
                    Para consultar la <strong>ubicación</strong> y los <strong>datos de transferencia</strong>, ve a <strong>Mi reserva</strong> e ingresa tu <strong>código de reserva</strong> (<strong>{esc(info_ok['codigo'])}</strong>).
                </div>
            </div>
        """), unsafe_allow_html=True)

    servicios_db = run_query("SELECT id, nombre, precio, duracion_minutos FROM servicios ORDER BY id ASC")
    servicios_dict = {f"{s[1]} · {clp(s[2])} CLP ({s[3]} min)": s[0] for s in servicios_db}

    disp_db = run_query("""
        SELECT id, fecha_hora FROM disponibilidades 
        WHERE disponible = TRUE 
          AND fecha_hora >= NOW() 
          AND fecha_hora <= NOW() + INTERVAL '14 days'
        ORDER BY fecha_hora ASC
    """)
    disp_dict = {d[1].strftime("%d/%m/%Y · %H:%M"): (d[0], d[1]) for d in disp_db}

    nonce = st.session_state["form_agenda_nonce"]

    col_form, col_info = st.columns([1.7, 1], gap="large")

    with col_form:
        with st.form(f"form_cliente_{nonce}", clear_on_submit=False):
            st.markdown("##### Tus datos")
            nombre = st.text_input("Nombre", max_chars=50, key=f"ag_nombre_{nonce}")
            apellido = st.text_input("Apellido", max_chars=50, key=f"ag_apellido_{nonce}")
            rut = st.text_input("RUT", placeholder="123456789", max_chars=9, key=f"ag_rut_{nonce}")
            correo = st.text_input("Correo electrónico", placeholder="tucorreo@ejemplo.com", max_chars=100, key=f"ag_correo_{nonce}")
            telefono = st.text_input("Teléfono", placeholder="912345678", max_chars=9, key=f"ag_tel_{nonce}")

            st.markdown("##### Tu cita")
            s1, s2 = st.columns(2)
            with s1:
                servicio_seleccionado = st.selectbox("Servicio", list(servicios_dict.keys()), key=f"ag_serv_{nonce}")
            with s2:
                if not disp_dict:
                    st.warning("Por el momento no hay horarios disponibles en las próximas 2 semanas.")
                    horario_elegido = None
                else:
                    horario_elegido = st.selectbox("Horario disponible", list(disp_dict.keys()), key=f"ag_hora_{nonce}")

            submitted = st.form_submit_button("Confirmar reserva", type="primary")

            if submitted:
                if not horario_elegido:
                    st.error("Debes seleccionar un horario disponible para poder agendar tu hora.")
                else:
                    valido, msg_error, rut_normalizado, tel_normalizado = validar_datos_agenda(
                        nombre, apellido, rut, correo, telefono
                    )
                    if not valido:
                        st.error(msg_error)
                    else:
                        try:
                            rut_sin_guion = rut_normalizado.replace("-", "")
                            cliente_existente = run_query(
                                "SELECT id, sancionado_hasta FROM clientes WHERE rut = %s OR rut = %s",
                                (rut_normalizado, rut_sin_guion)
                            )

                            correo_limpio = correo.strip().lower()
                            nombre_completo = f"{nombre.strip()} {apellido.strip()}"

                            if cliente_existente and cliente_existente[0][1]:
                                if cliente_existente[0][1] > datetime.now():
                                    st.error(
                                        f"Tu RUT tiene una restricción temporal hasta el "
                                        f"{cliente_existente[0][1].strftime('%d/%m/%Y a las %H:%M')} "
                                        "por haber alcanzado el límite de 3 modificaciones."
                                    )
                                    st.stop()

                            if not cliente_existente:
                                run_query(
                                    "INSERT INTO clientes (nombre, apellido, rut, correo, telefono) VALUES (%s, %s, %s, %s, %s)",
                                    (nombre.strip(), apellido.strip(), rut_normalizado, correo_limpio, tel_normalizado),
                                    fetch=False
                                )
                                cliente_id = run_query(
                                    "SELECT id FROM clientes WHERE rut = %s",
                                    (rut_normalizado,)
                                )[0][0]
                            else:
                                cliente_id = cliente_existente[0][0]
                                run_query(
                                    "UPDATE clientes SET nombre = %s, apellido = %s, correo = %s, telefono = %s WHERE id = %s",
                                    (nombre.strip(), apellido.strip(), correo_limpio, tel_normalizado, cliente_id),
                                    fetch=False
                                )

                            disp_id, fecha_hora_val = disp_dict[horario_elegido]

                            if bloque_tiene_reserva_activa(disp_id):
                                st.error("Ese horario acaba de ser tomado por otra persona. Por favor elige otro bloque disponible.")
                                st.stop()

                            codigo_reserva = generar_codigo_reserva()
                            servicio_id = servicios_dict[servicio_seleccionado]
                            nombre_servicio = servicio_seleccionado.split(" · ")[0]

                            run_query(
                                """
                                INSERT INTO reservas (reserva_codigo, cliente_id, servicio_id, disponibilidad_id, fecha_hora) 
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (codigo_reserva, cliente_id, servicio_id, disp_id, fecha_hora_val),
                                fetch=False
                            )

                            run_query("UPDATE disponibilidades SET disponible = FALSE WHERE id = %s", (disp_id,), fetch=False)

                            enviar_correo_confirmacion(
                                destinatario=correo_limpio,
                                nombre_clienta=nombre_completo,
                                codigo=codigo_reserva,
                                servicio=nombre_servicio,
                                horario=horario_elegido,
                                direccion_estudio=ubicacion_actual,
                            )

                            st.session_state["ultima_reserva_ok"] = {
                                "nombre": nombre_completo,
                                "codigo": codigo_reserva,
                                "servicio": nombre_servicio,
                                "horario": horario_elegido,
                                "correo": correo_limpio,
                                "ubicacion": ubicacion_actual,
                            }
                            st.session_state["form_agenda_nonce"] += 1
                            st.rerun()

                        except psycopg2.IntegrityError:
                            st.error("Ya existe un registro con esos datos. Por favor revisa tu RUT o correo e inténtalo nuevamente.")
                        except Exception:
                            st.error("Hubo un inconveniente al guardar tu reserva. Revisa que todos los datos estén correctos e inténtalo de nuevo.")

    with col_info:
        st.markdown(h("""
            <div class="soft-panel panel-lila">
                <h3>Antes de agendar</h3>
                <p><strong>• Ventana de reserva:</strong> Bloques disponibles dentro de las próximas 2 semanas.</p>
                <p><strong>• Ubicación:</strong> Se comparte al confirmar tu hora y en <strong>Mi reserva</strong>.</p>
                <p><strong>• Datos de transferencia:</strong> Consúltalos en <strong>Mi reserva</strong> con tu código.</p>
                <p><strong>• Cambios de hora:</strong> Hasta 3 modificaciones por reserva.</p>
            </div>
        """), unsafe_allow_html=True)


# ---------------------------------------------------------
# VISTA 3: CONSULTAR / MODIFICAR / ANULAR RESERVA
# ---------------------------------------------------------
elif vista == "Reserva":
    encabezado(
        "Gestión de citas",
        "Mi reserva",
        "Ingresa tu código de 6 caracteres para ver tu cita, ubicación, datos de transferencia o reagendar."
    )

    codigo_ingresado = st.text_input("Código de reserva", placeholder="Ej: KU06SQ", max_chars=6).upper().strip()

    if codigo_ingresado:
        if len(codigo_ingresado) != 6 or not codigo_ingresado.isalnum():
            st.error("Revisa tu código: debe tener exactamente 6 letras o números (ejemplo: KU06SQ).")
        else:
            try:
                reserva_data = run_query("""
                    SELECT R.id, R.estado, R.contador_modificaciones, R.fecha_hora, 
                           S.nombre, C.nombre, C.apellido, R.disponibilidad_id, R.cliente_id
                    FROM reservas R 
                    JOIN servicios S ON R.servicio_id = S.id 
                    JOIN clientes C ON R.cliente_id = C.id 
                    WHERE R.reserva_codigo = %s
                """, (codigo_ingresado,))

                if reserva_data:
                    r = reserva_data[0]
                    reserva_id, estado_actual, mod_count, fecha_actual, serv_nombre, cli_nombre, cli_apellido, disp_actual_id, cli_id = r

                    banco_reserva = run_query("""
                        SELECT banco_nombre, banco_tipo_cuenta, banco_numero_cuenta, banco_rut
                        FROM administradores
                        WHERE banco_numero_cuenta IS NOT NULL AND banco_numero_cuenta <> ''
                        LIMIT 1
                    """)
                    if banco_reserva:
                        bn, bt, bc, br = banco_reserva[0]
                        bloque_banco_html = f"""
                            <hr style="border:none; border-top:1px dashed #e9defa; margin:.9rem 0;">
                            <div style="font-weight:700; color:#3b0764; margin-bottom:.35rem;">Datos de transferencia</div>
                            <div class="info-row"><span>Banco</span><span>{esc(str(bn or '-'))}</span></div>
                            <div class="info-row"><span>Tipo de cuenta</span><span>{esc(str(bt or '-'))}</span></div>
                            <div class="info-row"><span>Número de cuenta</span><span>{esc(str(bc or '-'))}</span></div>
                            <div class="info-row"><span>RUT titular</span><span>{esc(str(br or '-'))}</span></div>
                        """
                    else:
                        bloque_banco_html = """
                            <hr style="border:none; border-top:1px dashed #e9defa; margin:.9rem 0;">
                            <div style="font-size:.86rem; color:#6b5b82;">Datos de transferencia pendientes de configuración en administración.</div>
                        """

                    st.markdown(h(f"""
                        <div class="soft-panel">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:.75rem;">
                                <div>
                                    <div style="font-size:.78rem; color:#6b5b82; font-weight:600; margin-bottom:.2rem;">CÓDIGO DE RESERVA</div>
                                    <span class="code-chip"><strong>{esc(codigo_ingresado)}</strong></span>
                                </div>
                                {badge_estado(estado_actual)}
                            </div>
                            <div class="info-row"><span>Clienta</span><span>{esc(f"{cli_nombre} {cli_apellido}")}</span></div>
                            <div class="info-row"><span>Servicio</span><span>{esc(str(serv_nombre))}</span></div>
                            <div class="info-row"><span>Fecha y hora</span><span>{fecha_actual.strftime('%d/%m/%Y %H:%M')}</span></div>
                            <div class="info-row"><span>Ubicación</span><span>{esc(ubicacion_actual)}</span></div>
                            <div class="info-row"><span>Modificaciones</span><span>{mod_count} / 3</span></div>
                            {bloque_banco_html}
                        </div>
                    """), unsafe_allow_html=True)

                    if estado_actual == 'Cancelada':
                        st.info("Esta reserva ya fue anulada.")
                    else:
                        col_1, col_2 = st.columns(2, gap="large")
                        with col_1:
                            if st.button("Anular reserva", type="secondary"):
                                run_query("UPDATE reservas SET estado = 'Cancelada' WHERE id = %s", (reserva_id,), fetch=False)
                                if disp_actual_id:
                                    run_query("UPDATE disponibilidades SET disponible = TRUE WHERE id = %s", (disp_actual_id,), fetch=False)
                                st.success("Tu reserva fue anulada y el horario quedó libre nuevamente.")
                                st.rerun()

                        with col_2:
                            if mod_count < 3:
                                nuevos_disp = run_query("""
                                    SELECT id, fecha_hora FROM disponibilidades 
                                    WHERE disponible = TRUE AND fecha_hora >= NOW() 
                                    ORDER BY fecha_hora ASC
                                """)
                                nuevos_dict = {d[1].strftime("%d/%m/%Y · %H:%M"): (d[0], d[1]) for d in nuevos_disp}

                                if nuevos_dict:
                                    nuevo_slot_label = st.selectbox("Selecciona nuevo horario disponible", list(nuevos_dict.keys()))
                                    if st.button("Confirmar cambio de hora", type="primary"):
                                        nuevo_disp_id, nueva_fecha_hora = nuevos_dict[nuevo_slot_label]
                                        if bloque_tiene_reserva_activa(nuevo_disp_id):
                                            st.error("Ese horario acaba de ser reservado. Por favor elige otro.")
                                        else:
                                            nuevo_contador = mod_count + 1

                                            # Liberar siempre el bloque anterior
                                            if disp_actual_id:
                                                run_query(
                                                    "UPDATE disponibilidades SET disponible = TRUE WHERE id = %s",
                                                    (disp_actual_id,),
                                                    fetch=False
                                                )

                                            if nuevo_contador >= 3:
                                                # En la 3.ª modificación: se cancela la reserva, no se ocupa el nuevo bloque,
                                                # se descuenta de ganancias y se sanciona por 7 días
                                                run_query("""
                                                    UPDATE reservas
                                                    SET disponibilidad_id = NULL,
                                                        contador_modificaciones = %s,
                                                        estado = 'Cancelada'
                                                    WHERE id = %s
                                                """, (nuevo_contador, reserva_id), fetch=False)

                                                sancion = datetime.now() + timedelta(days=7)
                                                run_query(
                                                    "UPDATE clientes SET sancionado_hasta = %s WHERE id = %s",
                                                    (sancion, cli_id),
                                                    fetch=False
                                                )
                                                st.warning(
                                                    "Alcanzaste el límite de 3 modificaciones. La reserva fue anulada automáticamente, "
                                                    "el horario quedó liberado y no podrás agendar nuevas horas por 1 semana."
                                                )
                                            else:
                                                # 1.ª y 2.ª modificación: ocupa el nuevo bloque y actualiza la reserva
                                                run_query(
                                                    "UPDATE disponibilidades SET disponible = FALSE WHERE id = %s",
                                                    (nuevo_disp_id,),
                                                    fetch=False
                                                )
                                                run_query("""
                                                    UPDATE reservas 
                                                    SET disponibilidad_id = %s, fecha_hora = %s, contador_modificaciones = %s, estado = 'Modificada' 
                                                    WHERE id = %s
                                                """, (nuevo_disp_id, nueva_fecha_hora, nuevo_contador, reserva_id), fetch=False)
                                                st.success(f"¡Hora reagendada! Te quedan {3 - nuevo_contador} modificaciones disponibles.")
                                            st.rerun()
                                else:
                                    st.warning("Por el momento no hay otros horarios disponibles para reagendar.")
                            else:
                                st.error("Ya alcanzaste el máximo de 3 modificaciones permitidas para esta reserva.")
                else:
                    st.error("No encontramos una reserva con ese código. Revisa que esté bien escrito (6 letras o números).")
            except Exception:
                st.error("No pudimos revisar tu reserva en este momento. Por favor intenta nuevamente.")


# ---------------------------------------------------------
# VISTA 4: CONTACTO Y DATOS DE TRANSFERENCIA (SIN UBICACIÓN PÚBLICA)
# ---------------------------------------------------------
elif vista == "Contacto":
    encabezado("Canales & Pagos", "Contacto", "Información de atención y datos para transferencia.")
    c_izq, c_der = st.columns(2, gap="large")

    with c_izq:
        st.markdown(h("""
            <div class="soft-panel">
                <h3>Glossy Rosse · Coquimbo</h3>
                <div class="info-row"><span>Ubicación</span><span>Se envía al reservar y en Mi reserva</span></div>
                <div class="info-row"><span>Instagram</span><span>@glossyrosse_</span></div>
                <div class="info-row"><span>Cambios de hora</span><span>Máximo 3 por reserva</span></div>
            </div>
        """), unsafe_allow_html=True)

    with c_der:
        banco_publico = run_query("""
            SELECT banco_nombre, banco_tipo_cuenta, banco_numero_cuenta, banco_rut
            FROM administradores
            WHERE banco_numero_cuenta IS NOT NULL AND banco_numero_cuenta <> ''
            LIMIT 1
        """)
        if banco_publico:
            bn, bt, bc, br = banco_publico[0]
            st.markdown(h(f"""
                <div class="soft-panel panel-lila">
                    <h3>Datos para transferencia</h3>
                    <div class="info-row"><span>Banco</span><span>{esc(str(bn or '-'))}</span></div>
                    <div class="info-row"><span>Tipo de cuenta</span><span>{esc(str(bt or '-'))}</span></div>
                    <div class="info-row"><span>Número de cuenta</span><span>{esc(str(bc or '-'))}</span></div>
                    <div class="info-row"><span>RUT titular</span><span>{esc(str(br or '-'))}</span></div>
                </div>
            """), unsafe_allow_html=True)
        else:
            st.info("Los datos bancarios se mostrarán aquí una vez configurados.")


# ---------------------------------------------------------
# VISTA 5: ACCESO MARTINA (PANEL DE ADMINISTRACIÓN)
# ---------------------------------------------------------
elif vista == "Admin":
    encabezado("Administración", "Acceso Martina", "Gestión de agenda, clientas, servicios, ubicación y datos bancarios.")

    if not st.session_state.get('auth', False):
        with st.form("login_admin"):
            admin_user = st.text_input("Usuario Administrador")
            admin_pass = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar Sesión Admin", type="primary"):
                admin_db = run_query(
                    "SELECT id, password_hash FROM administradores WHERE username = %s",
                    (admin_user.strip(),)
                )
                login_ok = False
                if admin_db and admin_db[0][1]:
                    hash_guardado = str(admin_db[0][1]).strip()
                    try:
                        login_ok = bcrypt.checkpw(
                            admin_pass.encode("utf-8"),
                            hash_guardado.encode("utf-8")
                        )
                    except ValueError:
                        login_ok = False

                if login_ok:
                    st.session_state['auth'] = True
                    st.session_state['admin_id'] = admin_db[0][0]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos. Verifica tus datos e inténtalo de nuevo.")

    if st.session_state.get('auth', False):
        top1, top2 = st.columns([5, 1])
        with top1:
            st.success("¡Sesión iniciada correctamente! Bienvenida, Martina.")
        with top2:
            if st.button("Cerrar Sesión", type="secondary"):
                st.session_state['auth'] = False
                st.session_state.pop('admin_id', None)
                st.rerun()

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Dashboard & Ganancias",
            "👥 Clientes Registrados",
            "📅 Gestionar Horarios & Calendario (2 Semanas)",
            "⚙️ Ajustes, Ubicación y Datos Bancarios"
        ])

        with tab1:
            ganancias = run_query("""
                SELECT SUM(S.precio) FROM reservas R 
                JOIN servicios S ON R.servicio_id = S.id 
                WHERE R.estado IN ('Confirmada', 'Modificada')
            """)
            total = ganancias[0][0] if ganancias and ganancias[0][0] else 0
            st.metric(label="Ingresos Totales Estimados", value=f"{clp(total)} CLP")

            st.markdown("#### Listado de Horas Agendadas")
            horas_agenda = run_query("""
                SELECT R.reserva_codigo, C.nombre, C.apellido, C.telefono, S.nombre, R.fecha_hora, R.estado 
                FROM reservas R 
                JOIN clientes C ON R.cliente_id = C.id 
                JOIN servicios S ON R.servicio_id = S.id 
                ORDER BY R.fecha_hora DESC
            """)
            for h_row in horas_agenda:
                st.markdown(h(f"""
                    <div class="service-item-card">
                        <div class="service-icon">{icono_servicio(h_row[4])}</div>
                        <div class="service-body">
                            <div class="service-name"><span class="code-chip-sm"><strong>{esc(str(h_row[0]))}</strong></span> · {esc(f"{h_row[1]} {h_row[2]}")}</div>
                            <div class="service-desc">✂️ {esc(str(h_row[4]))} · 📅 {h_row[5].strftime('%d/%m/%Y %H:%M')} · 📞 {esc(str(h_row[3]))}</div>
                        </div>
                        {badge_estado(h_row[6])}
                    </div>
                """), unsafe_allow_html=True)

        with tab2:
            clientes = run_query("SELECT nombre, apellido, rut, correo, telefono, sancionado_hasta FROM clientes ORDER BY id DESC")
            for c in clientes:
                sancionado = bool(c[5] and c[5] > datetime.now())
                sancion_badge = (
                    f'<span class="badge badge-warn">Sancionado hasta {c[5].strftime("%d/%m/%Y %H:%M")}</span>'
                    if sancionado else '<span class="badge badge-ok">Activo</span>'
                )
                st.markdown(h(f"""
                    <div class="service-item-card">
                        <div class="service-icon">💜</div>
                        <div class="service-body">
                            <div class="service-name">{esc(f"{c[0]} {c[1]}")}</div>
                            <div class="service-desc">RUT: {esc(str(c[2]))} · Correo: {esc(str(c[3]))} · Teléfono: {esc(str(c[4]))}</div>
                        </div>
                        {sancion_badge}
                    </div>
                """), unsafe_allow_html=True)

            with st.expander("Registrar cliente manualmente"):
                with st.form("manual_cliente", clear_on_submit=True):
                    mnombre = st.text_input("Nombre", max_chars=50)
                    mapellido = st.text_input("Apellido", max_chars=50)
                    mrut = st.text_input("RUT", placeholder="123456789", max_chars=9)
                    mcorreo = st.text_input("Correo", max_chars=100)
                    mtelefono = st.text_input("Teléfono", placeholder="912345678", max_chars=9)
                    if st.form_submit_button("Guardar Cliente", type="primary"):
                        valido, msg_err, rut_norm, tel_norm = validar_datos_agenda(
                            mnombre, mapellido, mrut, mcorreo, mtelefono
                        )
                        if not valido:
                            st.error(msg_err)
                        else:
                            try:
                                run_query(
                                    "INSERT INTO clientes (nombre, apellido, rut, correo, telefono) VALUES (%s, %s, %s, %s, %s)",
                                    (mnombre.strip(), mapellido.strip(), rut_norm, mcorreo.strip().lower(), tel_norm),
                                    fetch=False
                                )
                                st.success("Cliente registrado con éxito.")
                                st.rerun()
                            except Exception:
                                st.error("No se pudo registrar el cliente. Verifica que el RUT no esté ya registrado.")

        with tab3:
            ahora = datetime.now()
            fecha_actual_sistema = ahora.date()
            fecha_fin_ventana = fecha_actual_sistema + timedelta(days=14)

            st.markdown(
                f"#### Agregar Horarios Disponibles · Fecha actual: **{fecha_actual_sistema.strftime('%d/%m/%Y')}**"
            )
            st.caption(f"Ventana habilitada de 2 semanas: **{fecha_actual_sistema.strftime('%d/%m/%Y')}** al **{fecha_fin_ventana.strftime('%d/%m/%Y')}**.")

            with st.container():
                col_add1, col_add2, col_add3 = st.columns([1.4, 1.2, 1.4], vertical_alignment="bottom")
                with col_add1:
                    nueva_fecha = st.date_input(
                        "Fecha del bloque",
                        value=fecha_actual_sistema,
                        min_value=fecha_actual_sistema,
                        max_value=fecha_fin_ventana,
                        key="admin_nueva_fecha"
                    )
                with col_add2:
                    nueva_hora = st.time_input(
                        "Hora de inicio",
                        value=time(10, 0),
                        step=timedelta(minutes=30),
                        key="admin_nueva_hora"
                    )
                with col_add3:
                    st.markdown(
                        f"<div style='font-size:0.82rem; color:#6b5b82; margin-bottom:0.35rem;'>"
                        f"Bloque: <strong>{nueva_fecha.strftime('%d/%m/%Y')} · {nueva_hora.strftime('%H:%M')}</strong></div>",
                        unsafe_allow_html=True
                    )
                    btn_add_hora = st.button("➕ Añadir a la Agenda", type="primary", use_container_width=True)

            if btn_add_hora:
                fh_comb = datetime.combine(nueva_fecha, nueva_hora)
                if fh_comb <= ahora:
                    st.error("Elige una fecha y hora posterior a la hora actual para que aparezca disponible.")
                else:
                    admin_id = st.session_state.get('admin_id')
                    try:
                        run_query(
                            "INSERT INTO disponibilidades (fecha_hora, disponible, administrador_id) VALUES (%s, TRUE, %s)",
                            (fh_comb, admin_id),
                            fetch=False
                        )
                        st.success(f"Horario **{fh_comb.strftime('%d/%m/%Y · %H:%M')}** añadido a la agenda.")
                        st.rerun()
                    except Exception:
                        st.error("Ese horario ya existe en la agenda.")

            disp_list = run_query("""
                SELECT D.id, D.fecha_hora, D.disponible,
                       R.reserva_codigo, C.nombre, C.apellido, R.estado
                FROM disponibilidades D
                LEFT JOIN reservas R ON R.disponibilidad_id = D.id AND R.estado IN ('Confirmada', 'Modificada')
                LEFT JOIN clientes C ON R.cliente_id = C.id
                WHERE D.fecha_hora >= %s AND D.fecha_hora <= %s
                ORDER BY D.fecha_hora ASC
            """, (datetime.combine(fecha_actual_sistema, time.min), datetime.combine(fecha_fin_ventana, time.max)))

            st.markdown("---")
            st.markdown("#### Calendario Semanal de las Próximas 2 Semanas")

            por_fecha = {}
            for d_row in disp_list:
                dia_key = d_row[1].date()
                por_fecha.setdefault(dia_key, []).append(d_row)

            dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

            for num_sem in range(2):
                inicio_sem = fecha_actual_sistema + timedelta(days=num_sem * 7)
                fin_sem = min(inicio_sem + timedelta(days=6), fecha_fin_ventana)
                st.markdown(
                    f"**Semana {num_sem + 1}** ({inicio_sem.strftime('%d/%m/%Y')} – {fin_sem.strftime('%d/%m/%Y')})"
                )
                cols_sem = st.columns(7, gap="small")
                for idx_d in range(7):
                    dia_curr = inicio_sem + timedelta(days=idx_d)
                    with cols_sem[idx_d]:
                        if dia_curr > fecha_fin_ventana:
                            st.caption("—")
                            continue
                        etiqueta_hoy = " · Hoy" if dia_curr == fecha_actual_sistema else ""
                        nombre_dia = dias_esp[dia_curr.weekday()]
                        slots_dia = por_fecha.get(dia_curr, [])

                        partes_html = [
                            f'<div class="cal-day-card"><div class="cal-day-header">{nombre_dia} {dia_curr.strftime("%d/%m")}{etiqueta_hoy}</div>'
                        ]
                        if not slots_dia:
                            partes_html.append('<div style="font-size:0.78rem; color:#8b7ba3;">Sin bloques</div>')
                        else:
                            for s_item in slots_dia:
                                _, fh_s, _, res_c, c_nom, c_ape, _ = s_item
                                hora_txt = fh_s.strftime("%H:%M")
                                if res_c is not None:
                                    partes_html.append(
                                        f'<div class="cal-slot-busy">🔒 {esc(hora_txt)} · {esc(str(res_c))}<br><span style="font-weight:400;">{esc(f"{c_nom} {c_ape}")}</span></div>'
                                    )
                                else:
                                    partes_html.append(
                                        f'<div class="cal-slot-free">🟢 {esc(hora_txt)} · Libre</div>'
                                    )
                        partes_html.append("</div>")
                        st.markdown("".join(partes_html), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### Administrar Bloques Horarios (Editar / Eliminar)")

            if not disp_list:
                st.info("Aún no hay bloques horarios registrados en las próximas 2 semanas.")
            else:
                for d in disp_list:
                    disp_id, fh, es_disp, res_cod, cli_nom, cli_ape, res_est = d
                    tiene_reserva = res_cod is not None

                    c1, c2, c3 = st.columns([3.6, 1.4, 1.4], vertical_alignment="center")
                    with c1:
                        if tiene_reserva:
                            st.markdown(
                                f"🔒 **{fh.strftime('%d/%m/%Y · %H:%M')}** — Reservado por **{esc(f'{cli_nom} {cli_ape}')}** "
                                f"(<span class='code-chip-sm'><strong>{esc(str(res_cod))}</strong></span>)",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(f"🟢 **{fh.strftime('%d/%m/%Y · %H:%M')}** — Disponible")

                    with c2:
                        if not tiene_reserva:
                            with st.popover("✏️ Modificar"):
                                edit_fecha = st.date_input(
                                    "Nueva fecha",
                                    value=fh.date(),
                                    min_value=fecha_actual_sistema,
                                    max_value=fecha_fin_ventana,
                                    key=f"ef_{disp_id}"
                                )
                                edit_hora = st.time_input("Nueva hora", value=fh.time(), key=f"eh_{disp_id}")
                                if st.button("Guardar cambio", key=f"save_edit_{disp_id}"):
                                    if bloque_tiene_reserva_activa(disp_id):
                                        st.error("RF16: No se puede modificar porque ya tiene una hora agendada.")
                                    else:
                                        try:
                                            nueva_fh = datetime.combine(edit_fecha, edit_hora)
                                            run_query("UPDATE disponibilidades SET fecha_hora = %s WHERE id = %s", (nueva_fh, disp_id), fetch=False)
                                            st.success("Horario actualizado.")
                                            st.rerun()
                                        except Exception:
                                            st.error("Ya existe otro bloque con esa misma fecha y hora.")
                        else:
                            st.caption("Bloqueado (RF16)")

                    with c3:
                        if not tiene_reserva:
                            if st.button("🗑️ Eliminar", key=f"del_{disp_id}", type="secondary"):
                                if bloque_tiene_reserva_activa(disp_id):
                                    st.error("RF16: No se puede eliminar porque ya tiene una hora agendada.")
                                else:
                                    run_query("DELETE FROM disponibilidades WHERE id = %s", (disp_id,), fetch=False)
                                    st.success("Horario eliminado.")
                                    st.rerun()

        with tab4:
            st.markdown("#### Ubicación Privada para Clientas que Reserven")
            with st.form("form_ubicacion_admin"):
                nueva_ubicacion = st.text_input(
                    "Dirección de atención (solo visible al confirmar reserva y en Mi reserva)",
                    value=ubicacion_actual
                )
                if st.form_submit_button("Guardar Ubicación", type="primary"):
                    if not nueva_ubicacion.strip():
                        st.error("Ingresa una dirección válida.")
                    else:
                        run_query(
                            "UPDATE administradores SET ubicacion_estudio = %s;",
                            (nueva_ubicacion.strip(),),
                            fetch=False
                        )
                        st.success("Ubicación actualizada correctamente.")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### Precios y Duración de Servicios")
            servs = run_query("SELECT id, nombre, precio, duracion_minutos FROM servicios ORDER BY id ASC")
            for s in servs:
                col_s1, col_s2, col_s3 = st.columns([2, 2, 1], vertical_alignment="center")
                with col_s1:
                    nuevo_precio = st.number_input(f"Precio {s[1]} (CLP)", value=s[2], step=1000, key=f"serv_p_{s[0]}")
                with col_s2:
                    nueva_dur = st.number_input(f"Duración {s[1]} (min)", value=s[3], step=15, min_value=15, key=f"serv_d_{s[0]}")
                with col_s3:
                    if st.button("Actualizar", key=f"btn_{s[0]}"):
                        run_query("UPDATE servicios SET precio = %s, duracion_minutos = %s WHERE id = %s", (nuevo_precio, nueva_dur, s[0]), fetch=False)
                        st.success(f"{s[1]} actualizado.")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### Datos Bancarios para Transferencia")
            admin_id = st.session_state.get('admin_id')
            banco_data = run_query(
                "SELECT banco_nombre, banco_tipo_cuenta, banco_numero_cuenta, banco_rut FROM administradores WHERE id = %s",
                (admin_id,)
            )
            if banco_data:
                b_nom, b_tipo, b_num, b_rut = banco_data[0]
                with st.form("form_banco"):
                    new_b_nom = st.text_input("Banco", value=b_nom or "")
                    new_b_tipo = st.text_input("Tipo de Cuenta", value=b_tipo or "")
                    new_b_num = st.text_input("Número de Cuenta", value=b_num or "")
                    new_b_rut = st.text_input("RUT Titular", value=b_rut or "")
                    if st.form_submit_button("Guardar Datos Bancarios", type="primary"):
                        run_query("""
                            UPDATE administradores 
                            SET banco_nombre = %s, banco_tipo_cuenta = %s, banco_numero_cuenta = %s, banco_rut = %s 
                            WHERE id = %s
                        """, (new_b_nom, new_b_tipo, new_b_num, new_b_rut, admin_id), fetch=False)
                        st.success("Datos bancarios actualizados correctamente.")

            st.markdown("---")
            st.markdown("#### Cambiar o Regenerar Contraseña de Martina")
            with st.form("form_cambio_clave_admin", clear_on_submit=True):
                nueva_clave_1 = st.text_input("Nueva contraseña", type="password")
                nueva_clave_2 = st.text_input("Repetir nueva contraseña", type="password")
                if st.form_submit_button("Guardar Nueva Contraseña Encriptada", type="primary"):
                    if not nueva_clave_1 or len(nueva_clave_1) < 4:
                        st.error("Ingresa una contraseña de al menos 4 caracteres.")
                    elif nueva_clave_1 != nueva_clave_2:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        nuevo_hash = bcrypt.hashpw(nueva_clave_1.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                        run_query(
                            "UPDATE administradores SET password_hash = %s WHERE id = %s",
                            (nuevo_hash, admin_id),
                            fetch=False
                        )
                        st.success("Contraseña encriptada actualizada correctamente en la base de datos.")


# ---------------------------------------------------------
# PIE DE PÁGINA
# ---------------------------------------------------------
st.markdown(h("""
    <div class="site-footer">
        <strong>Glossy Rosse</strong> · Belleza &amp; Cuidado Personal · Coquimbo
    </div>
"""), unsafe_allow_html=True)
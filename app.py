from datetime import datetime, date, time, timedelta
from pathlib import Path
import random
import re
import string

import bcrypt
import psycopg2
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Glossy Rosse · Studio de Uñas & Belleza",
    page_icon="💅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DIRECCION_STUDIO = "Alberto Castex Taborga Poniente 1475"

DATOS_TRANSFERENCIA = {
    "Titular": "Martina",
    "Banco": "BancoEstado · CuentaRUT",
    "Tipo de cuenta": "Cuenta Vista / CuentaRUT",
    "Nota": "Envía tu comprobante indicando tu código de reserva.",
}

SERVICIOS_BASE = [
    {
        "nombre": "Manicure Permanente",
        "duracion_min": 60,
        "precio": 14000,
        "descripcion": "Limpieza profunda de cutícula, limado y esmaltado permanente de alta duración.",
    },
    {
        "nombre": "Kapping / Baño de Gel",
        "duracion_min": 75,
        "precio": 18000,
        "descripcion": "Capa protectora fortalecedora sobre tu uña natural con acabado brillante.",
    },
    {
        "nombre": "Soft Gel / Extensiones",
        "duracion_min": 90,
        "precio": 22000,
        "descripcion": "Alargamiento ligero y resistente con forma personalizada y esmaltado.",
    },
    {
        "nombre": "Nail Art & Diseño",
        "duracion_min": 30,
        "precio": 5000,
        "descripcion": "Diseños a mano alzada, efectos cromados, francesas o pedrería.",
    },
]

# -----------------------------------------------------------------------------
# ESTILOS CSS RESPONSIVOS (MÓVIL + ESCRITORIO) Y LIMPIEZA DE INPUTS
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    :root {
        --rose-bg: #fff9fb;
        --rose-card: #ffffff;
        --rose-soft: #fdeef3;
        --rose-border: #f3d5e0;
        --rose-primary: #c2527e;
        --rose-dark: #8f2d54;
        --text-main: #2d1f26;
        --text-muted: #6b5660;
    }

    .stApp {
        background-color: var(--rose-bg);
        color: var(--text-main);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: var(--rose-dark) !important;
    }

    /* Ocultar contadores de caracteres (ej. 0/9) en todos los text_input */
    [data-testid="InputInstructions"],
    div[data-baseweb="input"] + div,
    .stTextInput small {
        display: none !important;
    }

    /* Cabecera principal */
    .hero-box {
        background: linear-gradient(135deg, #fff0f5 0%, #ffe3ec 100%);
        border: 1px solid var(--rose-border);
        border-radius: 18px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.25rem;
        text-align: center;
    }

    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: var(--rose-dark);
        margin: 0;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        color: var(--text-muted);
        margin-top: 0.45rem;
        margin-bottom: 0;
    }

    /* Tarjetas de servicios */
    .service-card {
        background-color: var(--rose-card);
        border: 1px solid var(--rose-border);
        border-radius: 16px;
        padding: 1.2rem;
        height: 100%;
        box-shadow: 0 4px 14px rgba(194, 82, 126, 0.06);
        margin-bottom: 0.75rem;
    }

    .service-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.18rem;
        font-weight: 700;
        color: var(--rose-dark);
        margin-bottom: 0.35rem;
    }

    .service-meta {
        font-size: 0.88rem;
        font-weight: 600;
        color: var(--rose-primary);
        margin-bottom: 0.5rem;
    }

    .service-desc {
        font-size: 0.9rem;
        color: var(--text-muted);
        line-height: 1.45;
        margin: 0;
    }

    /* Tarjeta de confirmación / detalles de reserva */
    .confirm-card {
        background-color: #ffffff;
        border: 1.5px solid #e7a4be;
        border-left: 6px solid var(--rose-primary);
        border-radius: 16px;
        padding: 1.35rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 6px 20px rgba(143, 45, 84, 0.08);
    }

    .confirm-code {
        display: inline-block;
        background-color: var(--rose-soft);
        color: var(--rose-dark);
        font-weight: 700;
        font-size: 1.15rem;
        padding: 0.25rem 0.75rem;
        border-radius: 8px;
        letter-spacing: 0.5px;
    }

    /* Botones */
    .stButton > button, .stFormSubmitButton > button {
        background-color: var(--rose-primary) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }

    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background-color: var(--rose-dark) !important;
    }

    /* Pestañas adaptables */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        flex-wrap: wrap;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border: 1px solid var(--rose-border);
        border-radius: 10px;
        padding: 0.45rem 0.9rem;
        color: var(--text-main);
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--rose-primary) !important;
        color: #ffffff !important;
        border-color: var(--rose-primary) !important;
    }

    /* ---------------- RESPONSIVIDAD MÓVIL ---------------- */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-bottom: 2rem !important;
        }

        /* Apilar columnas en 1 sola columna en celular */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.75rem !important;
        }

        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        .hero-box {
            padding: 1.15rem 1rem;
        }

        .hero-title {
            font-size: 1.65rem;
        }

        .hero-subtitle {
            font-size: 0.9rem;
        }

        .confirm-card {
            padding: 1.05rem 1.1rem;
        }

        /* Evitar zoom automático en móviles al tocar inputs */
        input, textarea, select {
            font-size: 16px !important;
        }

        .stButton > button, .stFormSubmitButton > button {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS Y TABLAS
# -----------------------------------------------------------------------------
def get_db_connection():
    pg = st.secrets["postgres"]
    nombre_bd = pg.get("database") or pg.get("dbname") or pg.get("db_name") or "postgres"
    return psycopg2.connect(
        host=pg["host"],
        port=int(pg.get("port", 5432)),
        dbname=nombre_bd,
        user=pg["user"],
        password=pg["password"],
        sslmode=pg.get("sslmode", "require"),
    )


def init_db():
    """Asegura que existan las tablas necesarias sin perder datos existentes."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reservas_glossy (
                        id SERIAL PRIMARY KEY,
                        codigo VARCHAR(20) UNIQUE NOT NULL,
                        nombre_cliente VARCHAR(120) NOT NULL,
                        rut_cliente VARCHAR(12) NOT NULL,
                        telefono_cliente VARCHAR(15) NOT NULL,
                        servicio VARCHAR(120) NOT NULL,
                        precio INTEGER NOT NULL DEFAULT 0,
                        fecha DATE NOT NULL,
                        hora TIME NOT NULL,
                        estado VARCHAR(30) NOT NULL DEFAULT 'Confirmada',
                        notas TEXT,
                        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS disponibilidad_bloqueada (
                        id SERIAL PRIMARY KEY,
                        fecha DATE NOT NULL,
                        hora TIME,
                        todo_el_dia BOOLEAN NOT NULL DEFAULT FALSE,
                        motivo VARCHAR(150)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_glossy (
                        id SERIAL PRIMARY KEY,
                        usuario VARCHAR(60) UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    );
                    """
                )
                cur.execute("SELECT COUNT(*) FROM admin_glossy;")
                if cur.fetchone()[0] == 0:
                    default_pass = st.secrets.get("admin", {}).get("password", "Glossy2026!")
                    hashed = bcrypt.hashpw(default_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    cur.execute(
                        "INSERT INTO admin_glossy (usuario, password_hash) VALUES (%s, %s);",
                        ("Martina", hashed),
                    )
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# VALIDACIONES (RUT Y TELÉFONO)
# -----------------------------------------------------------------------------
def limpiar_rut_raw(valor: str) -> str:
    """Mantiene solo dígitos y K, máximo 9 caracteres."""
    limpio = re.sub(r"[^0-9kK]", "", valor or "").upper()
    return limpio[:9]


def validar_rut(rut_raw: str) -> tuple[bool, str, str]:
    """
    Valida un RUT ingresado sin puntos ni guion (8 o 9 caracteres: cuerpo + DV).
    Retorna (es_valido, rut_formateado, mensaje_error).
    """
    rut = limpiar_rut_raw(rut_raw)
    if len(rut) < 8 or len(rut) > 9:
        return False, "", "Ingresa un RUT válido de 8 o 9 dígitos (sin puntos ni guion)."

    cuerpo, dv = rut[:-1], rut[-1]
    if not cuerpo.isdigit():
        return False, "", "El cuerpo del RUT debe contener solo números."

    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1

    resto = 11 - (suma % 11)
    dv_esperado = "0" if resto == 11 else ("K" if resto == 10 else str(resto))

    if dv != dv_esperado:
        return False, "", "El RUT ingresado no es válido. Revisa el dígito verificador."

    rut_formateado = f"{int(cuerpo):,}".replace(",", ".") + f"-{dv}"
    return True, rut_formateado, ""


def limpiar_telefono_raw(valor: str) -> str:
    """Mantiene solo dígitos, máximo 9 números (ej. 912345678)."""
    solo_num = re.sub(r"\D", "", valor or "")
    return solo_num[:9]


def validar_telefono(tel_raw: str) -> tuple[bool, str, str]:
    """Valida teléfono móvil de 9 dígitos comenzando en 9."""
    tel = limpiar_telefono_raw(tel_raw)
    if len(tel) != 9 or not tel.startswith("9"):
        return False, "", "Ingresa un teléfono válido de 9 dígitos comenzando con 9 (ej. 912345678)."
    return True, f"+56 {tel[0]} {tel[1:5]} {tel[5:]}", ""


def generar_codigo_reserva() -> str:
    sufijo = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"GR-{sufijo}"


# -----------------------------------------------------------------------------
# RECURSOS VISUALES (LOGO Y GALERÍA)
# -----------------------------------------------------------------------------
def obtener_imagenes_proyecto() -> tuple[Path | None, list[Path]]:
    """Busca logo e imágenes en assets/galeria o carpetas locales del proyecto."""
    extensiones = {".png", ".jpg", ".jpeg", ".webp"}
    candidatos = []
    for carpeta in [Path("assets/galeria"), Path("assets"), Path(".")]:
        if carpeta.exists() and carpeta.is_dir():
            for archivo in sorted(carpeta.iterdir()):
                if archivo.is_file() and archivo.suffix.lower() in extensiones:
                    candidatos.append(archivo)

    logo = None
    galeria = []
    for img in candidatos:
        nombre_lower = img.name.lower()
        if "logo" in nombre_lower and logo is None:
            logo = img
        else:
            galeria.append(img)

    return logo, galeria


# -----------------------------------------------------------------------------
# OPERACIONES DE AGENDA Y CONSULTA
# -----------------------------------------------------------------------------
HORARIOS_DISPONIBLES = [
    time(10, 0),
    time(11, 30),
    time(13, 0),
    time(15, 0),
    time(16, 30),
    time(18, 0),
]


def obtener_horas_libres(fecha_sel: date) -> list[time]:
    if fecha_sel.weekday() == 6:  # Domingo cerrado
        return []

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT todo_el_dia, hora
                FROM disponibilidad_bloqueada
                WHERE fecha = %s;
                """,
                (fecha_sel,),
            )
            bloqueos = cur.fetchall()
            if any(b[0] for b in bloqueos):
                return []
            horas_bloqueadas = {b[1] for b in bloqueos if b[1] is not None}

            cur.execute(
                """
                SELECT hora
                FROM reservas_glossy
                WHERE fecha = %s AND estado != 'Cancelada';
                """,
                (fecha_sel,),
            )
            horas_ocupadas = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()

    ahora = datetime.now()
    libres = []
    for h in HORARIOS_DISPONIBLES:
        if h in horas_bloqueadas or h in horas_ocupadas:
            continue
        if fecha_sel == ahora.date() and datetime.combine(fecha_sel, h) <= ahora:
            continue
        libres.append(h)
    return libres


def crear_reserva(
    nombre: str,
    rut_formateado: str,
    telefono_formateado: str,
    servicio: str,
    precio: int,
    fecha_sel: date,
    hora_sel: time,
    notas: str,
) -> str:
    codigo = generar_codigo_reserva()
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM reservas_glossy
                    WHERE fecha = %s AND hora = %s AND estado != 'Cancelada';
                    """,
                    (fecha_sel, hora_sel),
                )
                if cur.fetchone()[0] > 0:
                    raise ValueError("Ese bloque horario acaba de ser ocupado. Por favor elige otro.")

                cur.execute(
                    """
                    INSERT INTO reservas_glossy
                        (codigo, nombre_cliente, rut_cliente, telefono_cliente, servicio, precio, fecha, hora, notas)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        codigo,
                        nombre.strip(),
                        rut_formateado,
                        telefono_formateado,
                        servicio,
                        precio,
                        fecha_sel,
                        hora_sel,
                        notas.strip(),
                    ),
                )
    finally:
        conn.close()
    return codigo


def buscar_reserva(codigo: str, rut_raw: str) -> dict | None:
    es_valido, rut_fmt, _ = validar_rut(rut_raw)
    if not es_valido:
        return None

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT codigo, nombre_cliente, rut_cliente, telefono_cliente,
                       servicio, precio, fecha, hora, estado, notas
                FROM reservas_glossy
                WHERE UPPER(codigo) = %s AND rut_cliente = %s;
                """,
                (codigo.strip().upper(), rut_fmt),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return {
        "codigo": row[0],
        "nombre": row[1],
        "rut": row[2],
        "telefono": row[3],
        "servicio": row[4],
        "precio": row[5],
        "fecha": row[6],
        "hora": row[7],
        "estado": row[8],
        "notas": row[9],
    }


# -----------------------------------------------------------------------------
# INTERFAZ PRINCIPAL
# -----------------------------------------------------------------------------
try:
    init_db()
except Exception as db_err:
    st.error(f"No fue posible conectar con la base de datos: {db_err}")
    st.stop()

logo_path, galeria_paths = obtener_imagenes_proyecto()

# Cabecera con Logo
if logo_path:
    c_logo_1, c_logo_2, c_logo_3 = st.columns([1.2, 1, 1.2])
    with c_logo_2:
        st.image(str(logo_path), use_container_width=True)

st.markdown(
    """
    <div class="hero-box">
        <h1 class="hero-title">Glossy Rosse</h1>
        <p class="hero-subtitle">Cuidado profesional de uñas, diseño personalizado y bienestar en cada detalle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_servicios, tab_agendar, tab_mi_reserva, tab_galeria, tab_admin = st.tabs(
    ["Servicios", "Agendar Hora", "Mi Reserva", "Galería", "Administración"]
)

# -----------------------------------------------------------------------------
# TAB 1: SERVICIOS (4 COLUMNAS EN ESCRITORIO, 1 COLUMNA EN CELULAR)
# -----------------------------------------------------------------------------
with tab_servicios:
    st.subheader("Nuestros Servicios")
    cols = st.columns(4)
    for idx, srv in enumerate(SERVICIOS_BASE):
        with cols[idx % 4]:
            precio_fmt = f"${srv['precio']:,}".replace(",", ".")
            st.markdown(
                f"""
                <div class="service-card">
                    <div class="service-title">{srv['nombre']}</div>
                    <div class="service-meta">{srv['duracion_min']} min · {precio_fmt}</div>
                    <p class="service-desc">{srv['descripcion']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -----------------------------------------------------------------------------
# TAB 2: AGENDAR HORA
# -----------------------------------------------------------------------------
with tab_agendar:
    st.subheader("Reserva tu cita")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        servicio_elegido = st.selectbox(
            "Servicio",
            options=[s["nombre"] for s in SERVICIOS_BASE],
        )
        srv_obj = next(s for s in SERVICIOS_BASE if s["nombre"] == servicio_elegido)
        st.caption(
            f"Duración estimada: {srv_obj['duracion_min']} min · Valor: "
            + f"${srv_obj['precio']:,}".replace(",", ".")
        )

    with col_f2:
        hoy = date.today()
        fecha_cita = st.date_input(
            "Fecha de atención",
            value=hoy,
            min_value=hoy,
            max_value=hoy + timedelta(days=30),
        )

    horas_disponibles = obtener_horas_libres(fecha_cita)

    if not horas_disponibles:
        st.warning("No hay bloques disponibles para la fecha seleccionada. Prueba con otro día.")
    else:
        with st.form("form_reserva_glossy", clear_on_submit=False):
            hora_cita = st.selectbox(
                "Horario disponible",
                options=horas_disponibles,
                format_func=lambda h: h.strftime("%H:%M hrs"),
            )

            c_datos1, c_datos2 = st.columns(2)
            with c_datos1:
                nombre_cliente = st.text_input("Nombre y apellido", placeholder="Ej. Camila Rojas")
                rut_input = st.text_input(
                    "RUT",
                    max_chars=9,
                    placeholder="Sin puntos ni guion (ej. 123456789)",
                )
            with c_datos2:
                telefono_input = st.text_input(
                    "Teléfono",
                    max_chars=9,
                    placeholder="9 dígitos (ej. 912345678)",
                )
                notas_cliente = st.text_input(
                    "Notas adicionales (opcional)",
                    placeholder="Ej. Diseño francés o retiro previo",
                )

            confirmar_btn = st.form_submit_button("Confirmar Reserva")

        if confirmar_btn:
            errores = []
            if len(nombre_cliente.strip()) < 3:
                errores.append("Ingresa tu nombre y apellido.")

            rut_ok, rut_fmt, rut_msg = validar_rut(rut_input)
            if not rut_ok:
                errores.append(rut_msg)

            tel_ok, tel_fmt, tel_msg = validar_telefono(telefono_input)
            if not tel_ok:
                errores.append(tel_msg)

            if errores:
                for e in errores:
                    st.error(e)
            else:
                try:
                    codigo_generado = crear_reserva(
                        nombre=nombre_cliente,
                        rut_formateado=rut_fmt,
                        telefono_formateado=tel_fmt,
                        servicio=srv_obj["nombre"],
                        precio=srv_obj["precio"],
                        fecha_sel=fecha_cita,
                        hora_sel=hora_cita,
                        notas=notas_cliente,
                    )
                    st.session_state["ultima_reserva"] = {
                        "codigo": codigo_generado,
                        "nombre": nombre_cliente.strip(),
                        "servicio": srv_obj["nombre"],
                        "fecha": fecha_cita.strftime("%d-%m-%Y"),
                        "hora": hora_cita.strftime("%H:%M hrs"),
                    }
                except Exception as exc:
                    st.error(f"No se pudo completar la reserva: {exc}")

    if "ultima_reserva" in st.session_state:
        res = st.session_state["ultima_reserva"]
        st.markdown(
            f"""
            <div class="confirm-card">
                <h3 style="margin-top:0;">¡Tu reserva ha sido confirmada!</h3>
                <p>Hola <strong>{res['nombre']}</strong>, te esperamos en <strong>Glossy Rosse</strong>.</p>
                <p><strong>Código de reserva:</strong> <span class="confirm-code">{res['codigo']}</span></p>
                <p><strong>Servicio:</strong> {res['servicio']}<br>
                   <strong>Fecha y hora:</strong> {res['fecha']} a las {res['hora']}<br>
                   <strong>Dirección:</strong> {DIRECCION_STUDIO}</p>
                <hr style="border:none; border-top:1px solid #f3d5e0; margin:12px 0;">
                <p style="margin-bottom:0; color:#5c3d4b;">
                    <strong>Importante:</strong> Para consultar nuevamente la ubicación y los datos de transferencia,
                    ve a la pestaña <strong>Mi Reserva</strong> e ingresa tu <strong>código de reserva</strong> junto con tu <strong>RUT</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# TAB 3: MI RESERVA (CONSULTA DE UBICACIÓN Y DATOS DE TRANSFERENCIA)
# -----------------------------------------------------------------------------
with tab_mi_reserva:
    st.subheader("Consulta tu Reserva")
    st.write("Ingresa tu **código de reserva** y tu **RUT** para revisar el estado de tu cita, la ubicación y los datos de transferencia.")

    with st.form("form_consultar_reserva"):
        c_bus1, c_bus2 = st.columns(2)
        with c_bus1:
            codigo_consulta = st.text_input("Código de reserva", placeholder="Ej. GR-A1B2C")
        with c_bus2:
            rut_consulta = st.text_input(
                "RUT",
                max_chars=9,
                placeholder="Sin puntos ni guion (ej. 123456789)",
            )
        buscar_btn = st.form_submit_button("Buscar Reserva")

    if buscar_btn:
        if not codigo_consulta.strip() or not rut_consulta.strip():
            st.warning("Completa tu código de reserva y tu RUT para buscar.")
        else:
            encontrada = buscar_reserva(codigo_consulta, rut_consulta)
            if not encontrada:
                st.error("No encontramos una reserva con ese código y RUT. Verifica los datos e intenta nuevamente.")
            else:
                precio_fmt = f"${encontrada['precio']:,}".replace(",", ".")
                st.markdown(
                    f"""
                    <div class="confirm-card">
                        <h3 style="margin-top:0;">Detalle de tu cita</h3>
                        <p><strong>Código de reserva:</strong> <span class="confirm-code">{encontrada['codigo']}</span></p>
                        <p><strong>Clienta:</strong> {encontrada['nombre']}<br>
                           <strong>Servicio:</strong> {encontrada['servicio']} ({precio_fmt})<br>
                           <strong>Fecha y hora:</strong> {encontrada['fecha'].strftime('%d-%m-%Y')} a las {encontrada['hora'].strftime('%H:%M hrs')}<br>
                           <strong>Estado:</strong> {encontrada['estado']}</p>
                        <hr style="border:none; border-top:1px solid #f3d5e0; margin:12px 0;">
                        <p><strong>Ubicación del estudio:</strong><br>{DIRECCION_STUDIO}</p>
                        <p style="margin-bottom:0;"><strong>Datos de transferencia:</strong><br>
                           Titular: {DATOS_TRANSFERENCIA['Titular']}<br>
                           Banco: {DATOS_TRANSFERENCIA['Banco']}<br>
                           Tipo de cuenta: {DATOS_TRANSFERENCIA['Tipo de cuenta']}<br>
                           <em>{DATOS_TRANSFERENCIA['Nota']}</em>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# -----------------------------------------------------------------------------
# TAB 4: GALERÍA (FOTOS DEL PROYECTO + LOGO)
# -----------------------------------------------------------------------------
with tab_galeria:
    st.subheader("Galería de Trabajos")
    if not galeria_paths:
        st.info("Sube tus fotos a la carpeta `assets/galeria` en tu repositorio para mostrarlas aquí.")
    else:
        cols_gal = st.columns(3)
        for idx, img_file in enumerate(galeria_paths):
            with cols_gal[idx % 3]:
                st.image(str(img_file), use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: ADMINISTRACIÓN (MARTINA)
# -----------------------------------------------------------------------------
with tab_admin:
    st.subheader("Panel de Administración")

    if "admin_autenticado" not in st.session_state:
        st.session_state["admin_autenticado"] = False

    if not st.session_state["admin_autenticado"]:
        with st.form("form_login_admin"):
            usuario_adm = st.text_input("Usuario", value="Martina")
            pass_adm = st.text_input("Contraseña", type="password")
            login_btn = st.form_submit_button("Ingresar")

        if login_btn:
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT password_hash FROM admin_glossy WHERE usuario = %s;",
                        (usuario_adm.strip(),),
                    )
                    row = cur.fetchone()
            finally:
                conn.close()

            if row and bcrypt.checkpw(pass_adm.encode("utf-8"), row[0].encode("utf-8")):
                st.session_state["admin_autenticado"] = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:
        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.success("Sesión iniciada como Martina")
        with col_top2:
            if st.button("Cerrar sesión"):
                st.session_state["admin_autenticado"] = False
                st.rerun()

        st.markdown("### Reservas Agendadas")
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, codigo, fecha, hora, nombre_cliente, rut_cliente,
                           telefono_cliente, servicio, estado, notas
                    FROM reservas_glossy
                    WHERE fecha >= CURRENT_DATE
                    ORDER BY fecha ASC, hora ASC;
                    """
                )
                filas = cur.fetchall()
        finally:
            conn.close()

        if not filas:
            st.info("No hay reservas próximas registradas.")
        else:
            for r in filas:
                r_id, r_cod, r_fec, r_hor, r_nom, r_rut, r_tel, r_srv, r_est, r_not = r
                with st.expander(
                    f"{r_fec.strftime('%d-%m-%Y')} · {r_hor.strftime('%H:%M')} — {r_nom} ({r_cod}) [{r_est}]"
                ):
                    st.write(f"**Servicio:** {r_srv}")
                    st.write(f"**RUT:** {r_rut} · **Teléfono:** {r_tel}")
                    if r_not:
                        st.write(f"**Notas:** {r_not}")

                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        if st.button("Marcar Completada", key=f"comp_{r_id}"):
                            conn = get_db_connection()
                            with conn:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        "UPDATE reservas_glossy SET estado = 'Completada' WHERE id = %s;",
                                        (r_id,),
                                    )
                            conn.close()
                            st.rerun()
                    with c_act2:
                        if st.button("Cancelar Reserva", key=f"canc_{r_id}"):
                            conn = get_db_connection()
                            with conn:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        "UPDATE reservas_glossy SET estado = 'Cancelada' WHERE id = %s;",
                                        (r_id,),
                                    )
                            conn.close()
                            st.rerun()

        st.markdown("### Bloquear Fecha u Horario (Próximas 2 semanas)")
        with st.form("form_bloqueo_admin"):
            b_fecha = st.date_input(
                "Fecha a bloquear",
                min_value=date.today(),
                max_value=date.today() + timedelta(days=14),
            )
            b_todo_dia = st.checkbox("Bloquear todo el día")
            b_hora = st.selectbox(
                "O elige un bloque específico",
                options=HORARIOS_DISPONIBLES,
                format_func=lambda h: h.strftime("%H:%M hrs"),
            )
            b_motivo = st.text_input("Motivo (opcional)", placeholder="Ej. Capacitación / Trámite")
            bloquear_btn = st.form_submit_button("Guardar Bloqueo")

        if bloquear_btn:
            conn = get_db_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO disponibilidad_bloqueada (fecha, hora, todo_el_dia, motivo)
                            VALUES (%s, %s, %s, %s);
                            """,
                            (b_fecha, None if b_todo_dia else b_hora, b_todo_dia, b_motivo.strip()),
                        )
                st.success("Bloqueo guardado correctamente.")
            finally:
                conn.close()
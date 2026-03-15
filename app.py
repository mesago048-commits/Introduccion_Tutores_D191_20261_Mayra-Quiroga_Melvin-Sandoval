import os
from supabase import create_client
from dotenv import load_dotenv
import streamlit as st
import datetime
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONEXIÓN SUPABASE
# ---------------------------
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# ---------------------------
# TRADUCCIÓN DÍAS
# ---------------------------
dias_semana = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# ---------------------------
# GENERAR HORARIOS
# ---------------------------
def generar_horas(inicio, fin):

    horas = []

    inicio = datetime.datetime.strptime(inicio, "%H:%M:%S")
    fin = datetime.datetime.strptime(fin, "%H:%M:%S")

    while inicio < fin:

        horas.append(inicio.strftime("%H:%M"))
        inicio += datetime.timedelta(minutes=45)

    return horas


# ---------------------------
# OBTENER DOCENTES
# ---------------------------
def obtener_docentes():

    respuesta = supabase.table("perfiles") \
        .select("*") \
        .eq("rol", "Docente") \
        .execute()

    return respuesta.data


# ---------------------------
# SESIÓN
# ---------------------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if "rol" not in st.session_state:
    st.session_state["rol"] = None


# ---------------------------
# MENÚ
# ---------------------------
if st.session_state["usuario"]:

    if st.session_state["rol"] == "Estudiante":

        st.sidebar.markdown(f"🎓 {st.session_state['usuario']}")

        menu = st.sidebar.radio(
            "Menú",
            ["Inicio", "Reservar", "Ver Reservas"]
        )

    elif st.session_state["rol"] == "Docente":

        st.sidebar.markdown(f"👨‍🏫 {st.session_state['usuario']}")

        menu = st.sidebar.radio(
            "Menú",
            ["Inicio", "Ver Mis Tutorías"]
        )

    elif st.session_state["rol"] == "Administrador":

        st.sidebar.markdown(f"🛠️ {st.session_state['usuario']}")

        menu = st.sidebar.radio(
            "Menú",
            ["Inicio", "Gestionar Usuarios", "Gestionar Reservas"]
        )

    if st.sidebar.button("Cerrar sesión"):

        st.session_state["usuario"] = None
        st.session_state["rol"] = None
        st.rerun()

else:

    menu = st.sidebar.radio(
        "Menú",
        ["Inicio", "Registro", "Login"]
    )


# ---------------------------
# INICIO
# ---------------------------
if menu == "Inicio":

    st.title("Sistema de Tutorías")


# ---------------------------
# REGISTRO
# ---------------------------
elif menu == "Registro":

    st.subheader("Registro")

    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")
    nombre = st.text_input("Nombre")

    rol = st.selectbox(
        "Rol",
        ["Estudiante", "Docente", "Administrador"]
    )

    materias = ""
    hora_inicio = ""
    hora_fin = ""
    dias = []

    if rol == "Docente":

        materias = st.text_input(
            "Materias que dictas (separadas por coma)"
        )

        dias = st.multiselect(
            "Días de tutoría",
            ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
            max_selections=3
        )

        hora_inicio = st.time_input("Hora inicio tutorías")
        hora_fin = st.time_input("Hora fin tutorías")

    if st.button("Registrar"):

        try:

            user = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            supabase.table("perfiles").insert({

                "id": user.user.id,
                "nombre": nombre,
                "rol": rol,
                "materias": materias,
                "hora_inicio": str(hora_inicio),
                "hora_fin": str(hora_fin),
                "dias_tutorias": ",".join(dias)

            }).execute()

            st.success("Usuario registrado")

        except Exception:

            st.error("Ese correo ya está registrado")


# ---------------------------
# LOGIN
# ---------------------------
elif menu == "Login":

    st.subheader("Iniciar sesión")

    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):

        try:

            user = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            perfil = supabase.table("perfiles") \
                .select("*") \
                .eq("id", user.user.id) \
                .execute()

            if perfil.data:

                st.session_state["usuario"] = perfil.data[0]["nombre"]
                st.session_state["rol"] = perfil.data[0]["rol"]

                st.success("Bienvenido")
                st.rerun()

        except Exception:

            st.error("Correo o contraseña incorrectos")


# ---------------------------
# RESERVAR
# ---------------------------
elif menu == "Reservar" and st.session_state["rol"] == "Estudiante":

    st.subheader("Reservar Tutoría")

    estudiante = st.session_state["usuario"]

    docentes = obtener_docentes()

    if not docentes:
        st.warning("No hay docentes registrados")
        st.stop()

    nombres_docentes = [d["nombre"] for d in docentes]

    docente_nombre = st.selectbox("Docente", nombres_docentes)

    docente = next((d for d in docentes if d["nombre"] == docente_nombre), None)

    materias_docente = docente["materias"].split(",") if docente.get("materias") else []

    materia = st.selectbox("Materia", materias_docente)

    dias_docente = docente.get("dias_tutorias", "")

    if dias_docente:
        dias_docente = dias_docente.split(",")
    else:
        dias_docente = []

    eventos = []

    hoy = datetime.date.today()

    for i in range(30):

        fecha_temp = hoy + datetime.timedelta(days=i)

        dia_es = dias_semana[fecha_temp.strftime("%A")]

        if dia_es in dias_docente:

            eventos.append({
                "title": "Tutorías disponibles",
                "start": str(fecha_temp),
                "color": "#2ECC71"
            })

    calendar(events=eventos, options={"initialView": "dayGridMonth"})

    fecha = st.date_input("Selecciona fecha", min_value=hoy)

    dia_seleccionado = dias_semana[fecha.strftime("%A")]

    if dia_seleccionado not in dias_docente:

        st.warning("Ese docente no da tutorías ese día")
        st.stop()

    horas_docente = generar_horas(docente["hora_inicio"], docente["hora_fin"])

    reservas = supabase.table("reservas") \
        .select("*") \
        .eq("docente", docente_nombre) \
        .eq("fecha", str(fecha)) \
        .execute().data

    horas_ocupadas = [r["hora"][:5] for r in reservas] if reservas else []

    horas_disponibles = [h for h in horas_docente if h not in horas_ocupadas]

    if not horas_disponibles:
        st.warning("No hay horarios disponibles ese día")
        st.stop()

    hora = st.selectbox("Hora disponible", horas_disponibles)

    if st.button("Reservar"):

        data = {
            "estudiante": estudiante,
            "docente": docente_nombre,
            "materia": materia,
            "fecha": str(fecha),
            "hora": hora
        }

        supabase.table("reservas").insert(data).execute()

        st.success("Tutoría reservada")


# ---------------------------
# VER RESERVAS (MEJORADO)
# ---------------------------
elif menu in ["Ver Reservas", "Ver Mis Tutorías", "Gestionar Reservas"]:

    reservas = supabase.table("reservas").select("*").execute().data

    if not reservas:
        st.warning("No hay tutorías registradas")
        st.stop()

    df = pd.DataFrame(reservas)

    if st.session_state["rol"] == "Estudiante":

        df = df[df["estudiante"] == st.session_state["usuario"]]

    elif st.session_state["rol"] == "Docente":

        df = df[df["docente"] == st.session_state["usuario"]]

    eventos = []

    for idx, row in df.iterrows():

        titulo = f"{row['hora']} - {row['materia']}"

        if st.session_state["rol"] == "Docente":
            titulo += f" ({row['estudiante']})"

        if st.session_state["rol"] == "Estudiante":
            titulo += f" ({row['docente']})"

        eventos.append({
            "title": titulo,
            "start": row["fecha"],
            "color": "#3498DB"
        })

    st.subheader("📅 Calendario de Tutorías")

    calendar(
        events=eventos,
        options={
            "initialView": "dayGridMonth",
            "height": 650
        }
    )

    st.subheader("Lista de Tutorías")

    st.dataframe(df)

    for idx, row in df.iterrows():

        if st.button(f"Cancelar tutoría {row['id']}"):

            supabase.table("reservas") \
                .delete() \
                .eq("id", row["id"]) \
                .execute()

            st.success("Tutoría cancelada")
            st.rerun()


# ---------------------------
# GESTIONAR USUARIOS
# ---------------------------
elif menu == "Gestionar Usuarios":

    usuarios = supabase.table("perfiles").select("*").execute().data

    if not usuarios:
        st.warning("No hay usuarios registrados")
        st.stop()

    df = pd.DataFrame(usuarios)

    st.dataframe(df)

    for idx, row in df.iterrows():

        if st.button(f"Eliminar {row['nombre']}"):

            supabase.table("perfiles") \
                .delete() \
                .eq("id", row["id"]) \
                .execute()

            st.rerun()
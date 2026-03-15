import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------
st.set_page_config(page_title="TUT0res 4.0", layout="wide")

# ---------------------------
# CONEXIÓN SUPABASE
# ---------------------------
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("Revisa los Secrets en Streamlit Cloud.")
        return None

supabase = init_connection()

# ---------------------------
# APOYO Y TRADUCCIÓN
# ---------------------------
dias_semana = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

def generar_horas(inicio, fin):
    horas = []
    try:
        fmt = "%H:%M:%S"
        t_inicio = datetime.datetime.strptime(str(inicio), fmt) if isinstance(inicio, str) else datetime.datetime.combine(datetime.date.today(), inicio)
        t_fin = datetime.datetime.strptime(str(fin), fmt) if isinstance(fin, str) else datetime.datetime.combine(datetime.date.today(), fin)
        while t_inicio < t_fin:
            horas.append(t_inicio.strftime("%H:%M"))
            t_inicio += datetime.timedelta(minutes=45)
    except: pass
    return horas

# ---------------------------
# SESIÓN Y MENÚ
# ---------------------------
if "usuario" not in st.session_state: st.session_state["usuario"] = None
if "rol" not in st.session_state: st.session_state["rol"] = None

st.sidebar.title("📌 TUT0res 4.0")

if st.session_state["usuario"]:
    st.sidebar.success(f"Conectado: {st.session_state['usuario']}")
    opciones = ["Inicio"]
    if st.session_state["rol"] == "Estudiante": opciones += ["Reservar", "Ver Reservas"]
    elif st.session_state["rol"] == "Docente": opciones += ["Ver Mis Tutorías"]
    elif st.session_state["rol"] == "Administrador": opciones += ["Gestionar Usuarios", "Gestionar Reservas"]
    
    menu = st.sidebar.radio("Navegación", opciones)
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
else:
    menu = st.sidebar.radio("Acceso", ["Inicio", "Registro", "Login"])

# ---------------------------
# MÓDULO: INICIO / REGISTRO / LOGIN
# ---------------------------
if menu == "Inicio":
    st.title("🚀 TUT0res - Salvemos la Universidad 4.0")

elif menu == "Registro":
    st.subheader("📝 Registro")
    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")
    nombre = st.text_input("Nombre completo")
    rol = st.selectbox("Rol", ["Estudiante", "Docente", "Administrador"])
    
    mats, h_in, h_out, ds = "", "08:00:00", "12:00:00", []
    if rol == "Docente":
        mats = st.text_input("Materias (separadas por coma)")
        ds = st.multiselect("Días", list(dias_semana.values()))
        h_in = str(st.time_input("Hora Inicio"))
        h_out = str(st.time_input("Hora Fin"))

    if st.button("Registrar"):
        try:
            u = supabase.auth.sign_up({"email": email, "password": password})
            if u.user:
                supabase.table("perfiles").insert({
                    "id": u.user.id, "nombre": nombre, "rol": rol,
                    "materias": mats, "hora_inicio": h_in, "hora_fin": h_out, "dias_tutorias": ",".join(ds)
                }).execute()
                st.success("Registrado. Logueate.")
        except: st.error("Error en registro.")

elif menu == "Login":
    st.subheader("🔑 Login")
    e, p = st.text_input("Email"), st.text_input("Password", type="password")
    if st.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": e, "password": p})
            per = supabase.table("perfiles").select("*").eq("id", res.user.id).execute()
            if per.data:
                st.session_state["usuario"], st.session_state["rol"] = per.data[0]["nombre"], per.data[0]["rol"]
                st.rerun()
        except: st.error("Datos incorrectos.")

# ---------------------------
# MÓDULO: RESERVAR (ESTUDIANTE)
# ---------------------------
elif menu == "Reservar" and st.session_state["rol"] == "Estudiante":
    st.subheader("📅 Reservar")
    docs = supabase.table("perfiles").select("*").eq("rol", "Docente").execute().data
    if docs:
        doc_nom = st.selectbox("Docente", [d["nombre"] for d in docs])
        d_sel = next(d for d in docs if d["nombre"] == doc_nom)
        
        # Calendario
        d_dis = d_sel.get("dias_tutorias", "").split(",")
        evs = []
        hoy = datetime.date.today()
        for i in range(30):
            f = hoy + datetime.timedelta(days=i)
            if dias_semana[f.strftime("%A")] in d_dis:
                evs.append({"title": "Disponible", "start": str(f), "color": "#2ECC71"})
        calendar(events=evs, options={"initialView": "dayGridMonth"})
        
        # Formulario
        mats = d_sel["materias"].split(",") if d_sel["materias"] else ["General"]
        mat_sel = st.selectbox("Materia", mats)
        f_sel = st.date_input("Fecha", min_value=hoy)
        
        if dias_semana[f_sel.strftime("%A")] in d_dis:
            hrs = generar_horas(d_sel["hora_inicio"], d_sel["hora_fin"])
            ocup = [r["hora"][:5] for r in supabase.table("reservas").select("hora").eq("docente", doc_nom).eq("fecha", str(f_sel)).execute().data]
            libres = [h for h in hrs if h not in ocup]
            if libres:
                h_sel = st.selectbox("Hora", libres)
                if st.button("Confirmar Reserva"):
                    try:
                        # NOTA: No enviamos ID para que Supabase use el 'Is Identity'
                        supabase.table("reservas").insert({
                            "estudiante": st.session_state["usuario"], "docente": doc_nom,
                            "materia": mat_sel, "fecha": str(f_sel), "hora": h_sel
                        }).execute()
                        st.success("¡Reservado!")
                        st.balloons()
                    except Exception as ex: st.error(f"Error de base de datos: {ex}")
            else: st.warning("Sin cupos.")
        else: st.error("Día no disponible.")

# ---------------------------
# MÓDULO: VER RESERVAS
# ---------------------------
elif menu in ["Ver Reservas", "Ver Mis Tutorías", "Gestionar Reservas"]:
    st.subheader("📋 Tutorías")
    res = supabase.table("reservas").select("*").execute().data
    if res:
        df = pd.DataFrame(res)
        if st.session_state["rol"] == "Estudiante": df = df[df["estudiante"] == st.session_state["usuario"]]
        elif st.session_state["rol"] == "Docente": df = df[df["docente"] == st.session_state["usuario"]]
        st.dataframe(df, use_container_width=True)
        
        for idx, row in df.iterrows():
            if st.button(f"Cancelar #{row['id']}", key=f"c_{row['id']}"):
                supabase.table("reservas").delete().eq("id", row["id"]).execute()
                st.rerun()

elif menu == "Gestionar Usuarios":
    st.subheader("👥 Usuarios")
    usr = supabase.table("perfiles").select("*").execute().data
    if usr:
        df_u = pd.DataFrame(usr)
        st.dataframe(df_u)
        for _, u in df_u.iterrows():
            if st.button(f"Eliminar {u['nombre']}", key=f"d_{u['id']}"):
                supabase.table("perfiles").delete().eq("id", u["id"]).execute()
                st.rerun()

import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------
st.set_page_config(page_title="TUT0res - Salvemos la Universidad 4.0", layout="wide")

# ---------------------------
# CONEXIÓN SUPABASE
# ---------------------------
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Error de configuración de credenciales.")
        return None

supabase = init_connection()

# ---------------------------
# TRADUCCIÓN DÍAS
# ---------------------------
dias_semana = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

# ---------------------------
# FUNCIONES DE APOYO
# ---------------------------
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

def obtener_docentes():
    try:
        respuesta = supabase.table("perfiles").select("*").eq("rol", "Docente").execute()
        return respuesta.data
    except: return []

# ---------------------------
# GESTIÓN DE SESIÓN
# ---------------------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "rol" not in st.session_state:
    st.session_state["rol"] = None

# ---------------------------
# MENÚ LATERAL
# ---------------------------
st.sidebar.title("📌 TUT0res 4.0")

if st.session_state["usuario"]:
    icono = "🎓" if st.session_state["rol"] == "Estudiante" else "👨‍🏫" if st.session_state["rol"] == "Docente" else "🛠️"
    st.sidebar.markdown(f"{icono} {st.session_state['usuario']}")
    opciones = ["Inicio"]
    if st.session_state["rol"] == "Estudiante":
        opciones += ["Reservar", "Ver Reservas"]
    elif st.session_state["rol"] == "Docente":
        opciones += ["Ver Mis Tutorías"]
    elif st.session_state["rol"] == "Administrador":
        opciones += ["Gestionar Usuarios", "Gestionar Reservas"]
    
    menu = st.sidebar.radio("Menú", opciones)
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
else:
    menu = st.sidebar.radio("Menú", ["Inicio", "Registro", "Login"])

# ---------------------------
# MÓDULOS
# ---------------------------
if menu == "Inicio":
    st.title("🚀 TUT0res - Salvemos la Universidad 4.0")
    st.markdown("### Bienvenido al sistema de gestión de tutorías académicas.")

elif menu == "Registro":
    st.subheader("📝 Registro de Usuario")
    col1, col2 = st.columns(2)
    with col1:
        email_reg = st.text_input("Correo electrónico", key="reg_email")
        pass_reg = st.text_input("Contraseña", type="password", key="reg_pass")
        nombre_reg = st.text_input("Nombre completo")
    with col2:
        rol_reg = st.selectbox("Rol", ["Estudiante", "Docente", "Administrador"])
        materias, dias, h_inicio, h_fin = "", [], datetime.time(8,0), datetime.time(12,0)
        if rol_reg == "Docente":
            materias = st.text_input("Materias (separadas por coma)")
            dias = st.multiselect("Días de tutoría", list(dias_semana.values()))
            h_inicio = st.time_input("Hora inicio")
            h_fin = st.time_input("Hora fin")

    if st.button("Registrar"):
        try:
            user = supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
            if user.user:
                supabase.table("perfiles").insert({
                    "id": user.user.id, "nombre": nombre_reg, "rol": rol_reg,
                    "materias": materias, "hora_inicio": str(h_inicio),
                    "hora_fin": str(h_fin), "dias_tutorias": ",".join(dias)
                }).execute()
                st.success("✅ Registro exitoso.")
        except: st.error("Error en el registro.")

elif menu == "Login":
    st.subheader("🔑 Iniciar sesión")
    email_log = st.text_input("Correo")
    pass_log = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email_log, "password": pass_log})
            perfil = supabase.table("perfiles").select("*").eq("id", res.user.id).execute()
            if perfil.data:
                st.session_state["usuario"] = perfil.data[0]["nombre"]
                st.session_state["rol"] = perfil.data[0]["rol"]
                st.rerun()
        except: st.error("Credenciales inválidas.")

elif menu == "Reservar" and st.session_state["rol"] == "Estudiante":
    st.subheader("📅 Reservar Tutoría")
    docentes = obtener_docentes()
    if docentes:
        docente_nombre = st.selectbox("Docente", [d["nombre"] for d in docentes])
        docente = next(d for d in docentes if d["nombre"] == docente_nombre)
        
        # Calendario Visual
        dias_doc = docente.get("dias_tutorias", "").split(",") if docente.get("dias_tutorias") else []
        eventos_disp = []
        hoy = datetime.date.today()
        for i in range(30):
            f = hoy + datetime.timedelta(days=i)
            if dias_semana[f.strftime("%A")] in dias_doc:
                eventos_disp.append({"title": "Disponible", "start": str(f), "color": "#2ECC71"})
        calendar(events=eventos_disp, options={"initialView": "dayGridMonth"})
        
        st.divider()
        materia_sel = st.selectbox("Materia", docente["materias"].split(",") if docente.get("materias") else ["General"])
        fecha_res = st.date_input("Fecha", min_value=hoy)
        
        if dias_semana[fecha_res.strftime("%A")] in dias_doc:
            horas_doc = generar_horas(docente["hora_inicio"], docente["hora_fin"])
            res_db = supabase.table("reservas").select("hora").eq("docente", docente_nombre).eq("fecha", str(fecha_res)).execute().data
            libres = [h for h in horas_doc if h not in [r["hora"][:5] for r in res_db]]
            if libres:
                hora_sel = st.selectbox("Hora", libres)
                if st.button("Confirmar Reserva"):
                    try:
                        # Mandamos los datos sin el 'id' para que Supabase use el 'Is Identity'
                        supabase.table("reservas").insert({
                            "estudiante": st.session_state["usuario"], "docente": docente_nombre,
                            "materia": materia_sel, "fecha": str(fecha_res), "hora": hora_sel
                        }).execute()
                        st.success("✅ ¡Tutoría agendada!")
                        st.balloons()
                    except Exception as e: st.error(f"Error: {e}")
            else: st.warning("Sin cupos.")
        else: st.error("Docente no disponible este día.")

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

elif menu == "Gestionar Usuarios" and st.session_state["rol"] == "Administrador":
    st.subheader("👥 Usuarios")
    usr = supabase.table("perfiles").select("*").execute().data
    if usr:
        df_u = pd.DataFrame(usr)
        st.dataframe(df_u)
        for _, u in df_u.iterrows():
            if st.button(f"Eliminar {u['nombre']}", key=f"d_{u['id']}"):
                supabase.table("perfiles").delete().eq("id", u["id"]).execute()
                st.rerun()
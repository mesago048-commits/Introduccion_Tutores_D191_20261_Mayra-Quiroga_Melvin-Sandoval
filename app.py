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
# CONEXIÓN SUPABASE (OPTIMIZADA PARA LA NUBE)
# ---------------------------
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Error de configuración de credenciales. Revisa los Secrets en Streamlit Cloud.")
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
    except:
        pass
    return horas

def obtener_docentes():
    try:
        respuesta = supabase.table("perfiles").select("*").eq("rol", "Docente").execute()
        return respuesta.data
    except:
        return []

# ---------------------------
# GESTIÓN DE SESIÓN
# ---------------------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "rol" not in st.session_state:
    st.session_state["rol"] = None

# ---------------------------
# MENÚ LATERAL (SIDEBAR)
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
# MÓDULO: INICIO
# ---------------------------
if menu == "Inicio":
    st.title("🚀 TUT0res - Salvemos la Universidad 4.0")
    st.markdown("### Bienvenido al sistema de gestión de tutorías académicas.")
    st.info("Selecciona una opción en el menú lateral para comenzar.")

# ---------------------------
# MÓDULO: REGISTRO
# ---------------------------
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
            materias = st.text_input("Materias que dictas (separadas por coma)")
            dias = st.multiselect("Días de tutoría", list(dias_semana.values()), max_selections=3)
            h_inicio = st.time_input("Hora inicio tutorías")
            h_fin = st.time_input("Hora fin tutorías")

    if st.button("Registrar"):
        try:
            user = supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
            if user.user:
                supabase.table("perfiles").insert({
                    "id": user.user.id, "nombre": nombre_reg, "rol": rol_reg,
                    "materias": materias, "hora_inicio": str(h_inicio),
                    "hora_fin": str(h_fin), "dias_tutorias": ",".join(dias)
                }).execute()
                st.success("✅ Usuario registrado con éxito. Ya puedes iniciar sesión.")
        except:
            st.error("Error en el registro. Es posible que el correo ya exista.")

# ---------------------------
# MÓDULO: LOGIN (CORREGIDO)
# ---------------------------
elif menu == "Login":
    st.subheader("🔑 Iniciar sesión")
    email_log = st.text_input("Correo")
    pass_log = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        login_exito = False
        try:
            res = supabase.auth.sign_in_with_password({"email": email_log, "password": pass_log})
            perfil = supabase.table("perfiles").select("*").eq("id", res.user.id).execute()
            if perfil.data:
                st.session_state["usuario"] = perfil.data[0]["nombre"]
                st.session_state["rol"] = perfil.data[0]["rol"]
                login_exito = True
        except:
            st.error("Correo o contraseña incorrectos.")
        
        if login_exito:
            st.success(f"Bienvenido {st.session_state['usuario']}")
            st.rerun()

# ---------------------------
# MÓDULO: RESERVAR (ESTUDIANTES)
# ---------------------------
elif menu == "Reservar" and st.session_state["rol"] == "Estudiante":
    st.subheader("📅 Reservar Tutoría")
    docentes = obtener_docentes()
    if not docentes:
        st.warning("No hay docentes registrados.")
    else:
        nombres_docentes = [d["nombre"] for d in docentes]
        docente_nombre = st.selectbox("Selecciona al Docente", nombres_docentes)
        docente = next((d for d in docentes if d["nombre"] == docente_nombre), None)
        
        dias_docente = docente.get("dias_tutorias", "").split(",") if docente.get("dias_tutorias") else []
        eventos_disp = []
        hoy = datetime.date.today()
        for i in range(30):
            f_temp = hoy + datetime.timedelta(days=i)
            if dias_semana[f_temp.strftime("%A")] in dias_docente:
                eventos_disp.append({"title": "Disponible", "start": str(f_temp), "color": "#2ECC71"})
        
        st.write("Días disponibles del docente (en verde):")
        calendar(events=eventos_disp, options={"initialView": "dayGridMonth"})
        
        st.divider()
        mats_doc = docente["materias"].split(",") if docente.get("materias") else ["General"]
        materia_sel = st.selectbox("Materia", mats_doc)
        fecha_res = st.date_input("Selecciona fecha", min_value=hoy)
        
        if dias_semana[fecha_res.strftime("%A")] not in dias_docente:
            st.error(f"❌ El docente no atiende los días {dias_semana[fecha_res.strftime('%A')]}")
        else:
            horas_doc = generar_horas(docente["hora_inicio"], docente["hora_fin"])
            res_db = supabase.table("reservas").select("hora").eq("docente", docente_nombre).eq("fecha", str(fecha_res)).execute().data
            ocupadas = [r["hora"][:5] for r in res_db] if res_db else []
            libres = [h for h in horas_doc if h not in ocupadas]
            
            if not libres:
                st.warning("No hay horarios disponibles.")
            else:
                hora_sel = st.selectbox("Horas disponibles", libres)
                if st.button("Confirmar Reserva"):
                    supabase.table("reservas").insert({
                        "estudiante": st.session_state["usuario"], "docente": docente_nombre,
                        "materia": materia_sel, "fecha": str(fecha_res), "hora": hora_sel
                    }).execute()
                    st.success("✅ Tutoría reservada con éxito.")

# ---------------------------
# MÓDULO: VER RESERVAS
# ---------------------------
elif menu in ["Ver Reservas", "Ver Mis Tutorías", "Gestionar Reservas"]:
    st.subheader("📋 Listado de Tutorías")
    res_data = supabase.table("reservas").select("*").execute().data
    if not res_data:
        st.info("No hay tutorías registradas.")
    else:
        df = pd.DataFrame(res_data)
        if st.session_state["rol"] == "Estudiante":
            df = df[df["estudiante"] == st.session_state["usuario"]]
        elif st.session_state["rol"] == "Docente":
            df = df[df["docente"] == st.session_state["usuario"]]
        
        st.dataframe(df, use_container_width=True)
        
        eventos_res = []
        for _, r in df.iterrows():
            titulo = f"{r['hora']} - {r['materia']}"
            eventos_res.append({"title": titulo, "start": r["fecha"], "color": "#3498DB"})
        
        calendar(events=eventos_res, options={"initialView": "dayGridMonth", "height": 500})
        
        for idx, row in df.iterrows():
            if st.button(f"Cancelar tutoría #{row['id']}", key=f"btn_{row['id']}"):
                supabase.table("reservas").delete().eq("id", row["id"]).execute()
                st.rerun()

# ---------------------------
# MÓDULO: GESTIONAR USUARIOS
# ---------------------------
elif menu == "Gestionar Usuarios" and st.session_state["rol"] == "Administrador":
    st.subheader("👥 Gestión de Perfiles")
    usuarios = supabase.table("perfiles").select("*").execute().data
    if usuarios:
        df_u = pd.DataFrame(usuarios)
        st.dataframe(df_u)
        for _, u in df_u.iterrows():
            if st.button(f"Eliminar a {u['nombre']}", key=f"del_{u['id']}"):
                supabase.table("perfiles").delete().eq("id", u["id"]).execute()
                st.rerun()
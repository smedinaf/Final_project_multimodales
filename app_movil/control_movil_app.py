import streamlit as st
import paho.mqtt.client as mqtt
import json
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
import io

st.set_page_config(page_title="Control Comedero Móvil", layout="centered")
st.title("📱 Panel de Control: Coco & Canela")

BROKER_IP = "157.230.214.127"
PORT = 1883
TOPIC_DIGITAL = "cmqtt_sdesi"
CLIENT_ID = "stream_client_usuario_mobile"

@st.cache_resource
def conectar_mqtt():
    cliente = mqtt.Client(CLIENT_ID)
    try:
        cliente.connect(BROKER_IP, PORT, 60)
        cliente.loop_start()
    except Exception as e:
        st.error(f"Error de conexión al Broker: {e}")
    return cliente

client = conectar_mqtt()

def enviar_comando_motor(estado_motor):
    # Enviamos la orden directa del motor. La pantalla se mantiene en "Nadie" o "Keep"
    payload = json.dumps({
        "Pantalla": "IGNORE", 
        "Act1": estado_motor
    })
    try:
        client.publish(TOPIC_DIGITAL, payload, qos=1)
        st.toast(f"📡 Comando '{estado_motor}' enviado a Wokwi", icon="🚀")
    except Exception as e:
        st.error(f"No se pudo enviar la orden: {e}")

# --- INTERFAZ DE BOTONES RÁPIDOS ---
st.subheader("⚡ Control Manual")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔓 Abrir Coco", use_container_width=True):
        enviar_comando_motor("GATO_A")
with col2:
    if st.button("🔓 Abrir Canela", use_container_width=True):
        enviar_comando_motor("GATO_B")
with col3:
    if st.button("🔒 Cerrar Todo", type="primary", use_container_width=True):
        enviar_comando_motor("NADIE")

# --- INTERFAZ DE VOZ ---
st.markdown("---")
st.subheader("🎙️ Control por Voz")

audio_grabado = mic_recorder(
    start_prompt="Mantén presionado para hablar 🎤",
    stop_prompt="Soltar para enviar 🟥",
    just_once=True,
    format="wav",
    key="mic_celular"
)

if audio_grabado:
    audio_bytes = audio_grabado['bytes']
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            texto_detectado = recognizer.recognize_google(audio_data, language="es-ES")
            
            st.info(f"Escuchado: \"{texto_detectado}\"")
            comando = texto_detectado.lower()
            
            if "coco" in comando:
                enviar_comando_motor("GATO_A")
                st.success("Abriendo plato de Coco")
            elif "canela" in comando:
                enviar_comando_motor("GATO_B")
                st.success("Abriendo plato de Canela")
            elif any(w in comando for w in ["cerrar", "quitar", "nadie", "bloquear"]):
                enviar_comando_motor("NADIE")
                st.error("Cerrando comederos")
            else:
                st.warning("Comando no detectado explícitamente. Intenta nombrar a 'Coco' o 'Canela'.")
    except sr.UnknownValueError:
        st.error("No se entendió el audio, ¡intenta de nuevo!")
    except Exception as e:
        st.error(f"Error procesando audio: {e}")

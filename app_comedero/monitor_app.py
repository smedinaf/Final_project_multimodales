import streamlit as st
from camera_input_live import camera_input_live
from PIL import Image, ImageOps
import numpy as np
import tensorflow as tf
import paho.mqtt.client as mqtt
import json

st.set_page_config(page_title="Sistema Comedero - Monitor", layout="centered")
st.title("📹 Monitor Activo: Coco y Canela")

BROKER_IP = "157.230.214.127"
PORT = 1883
TOPIC_DIGITAL = "cmqtt_sdesi"
CLIENT_ID = "comedero_monitor_ia"

@st.cache_resource
def inicializar_recursos():
    try:
        modelo_keras = tf.keras.models.load_model('keras_model.h5', compile=False)
    except Exception as e:
        modelo_keras = None
        st.error(f"Error al cargar el modelo: {e}")
        
    cliente_mqtt = mqtt.Client(CLIENT_ID)
    try:
        cliente_mqtt.connect(BROKER_IP, PORT, 60)
        cliente_mqtt.loop_start()
    except Exception as e:
        st.error(f"Error MQTT: {e}")
        
    return modelo_keras, cliente_mqtt

model, client1 = inicializar_recursos()
ETIQUETAS = ["Coco", "Canela", "Nadie"]

if "ultimo_michi_visto" not in st.session_state: st.session_state.ultimo_michi_visto = "Nadie"
if "contador_estabilidad" not in st.session_state: st.session_state.contador_estabilidad = 0
if "michi_candidato" not in st.session_state: st.session_state.michi_candidato = "Nadie"

def enviar_presencia_gato(gato):
    payload = json.dumps({
        "Pantalla": gato,
        "Act1": "MUTED" # La pantalla no sobreescribe las órdenes del motor del celular
    })
    try:
        client1.publish(TOPIC_DIGITAL, payload, qos=1)
    except Exception as e:
        st.error(f"Error al enviar datos: {e}")

def procesar_y_clasificar(imagen_pil):
    if model is None: return "Nadie", 0.0
    size = (224, 224)
    image = ImageOps.fit(imagen_pil, size, Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1.0
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array
    prediction = model.predict(data, verbose=0)
    return ETIQUETAS[np.argmax(prediction[0])], np.max(prediction[0])

# Pipeline de visión continuo
imagen_feed = camera_input_live(width=420, height=315, debounce=900)
if imagen_feed:
    st.image(imagen_feed, caption="Cámara del Comedero", use_container_width=True)
    img_pil = Image.open(imagen_feed).convert("RGB")
    resultado, confianza = procesar_y_clasificar(img_pil)
    
    st.metric(label="Identificado", value=resultado, delta=f"{confianza*100:.1f}% Confianza")
    
    michi_detectado_ahora = resultado if confianza > 0.75 else "Nadie"
    
    if michi_detectado_ahora == st.session_state.michi_candidato:
        st.session_state.contador_estabilidad += 1
    else:
        st.session_state.michi_candidato = michi_detectado_ahora
        st.session_state.contador_estabilidad = 0
        
    if st.session_state.contador_estabilidad >= 2:
        if michi_detectado_ahora != st.session_state.ultimo_michi_visto:
            st.session_state.ultimo_michi_visto = michi_detectado_ahora
            enviar_presencia_gato(michi_detectado_ahora)

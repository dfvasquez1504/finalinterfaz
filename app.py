import json
import threading

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_mic_recorder import speech_to_text
import paho.mqtt.client as mqtt

# =============== CONFIG STREAMLIT ===============
st.set_page_config(
    page_title="Dashboard IoT – ESP32",
    page_icon="🌡️",
    layout="wide",
)

st.title("🌡️ Dashboard IoT – ESP32 (DHT22, gas, luz, servo, LED)")

# =============== CONFIG MQTT ===============
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC_DATA = "Sensor/THP2"           # donde el ESP32 publica los sensores
MQTT_TOPIC_CMD_VENT = "Sensor/cmd/vent"   # para encender/apagar ventilador (LED)
MQTT_TOPIC_CMD_LAMP = "Sensor/cmd/lamp"   # para encender/apagar lámpara

# Diccionario global con el último mensaje recibido
latest_data = {
    "Temp": None,
    "Hum": None,
    "Luz": None,
    "Gas_ppm": None,
    "Servo_deg": None,
    "LED_temp": None,
}

latest_data_lock = threading.Lock()


# =============== CALLBACKS MQTT ===============
def on_connect(client, userdata, flags, rc):
    print("Conectado a MQTT con código", rc)
    client.subscribe(MQTT_TOPIC_DATA)


def on_message(client, userdata, msg):
    global latest_data
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        with latest_data_lock:
            for k, v in data.items():
                latest_data[k] = v
    except Exception as e:
        print("Error procesando mensaje MQTT:", e)


def init_mqtt():
    """Crea el cliente MQTT una sola vez y lo guarda en session_state."""
    if "mqtt_client" not in st.session_state:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        st.session_state.mqtt_client = client
    return st.session_state.mqtt_client


mqtt_client = init_mqtt()

# =============== AUTOREFRESH CADA 3 s ===============
st_autorefresh(interval=3000, key="sensor_autorefresh")

# =============== LECTURA DE DATOS ===============
with latest_data_lock:
    temp = latest_data.get("Temp")
    hum = latest_data.get("Hum")
    luz = latest_data.get("Luz")
    gas_ppm = latest_data.get("Gas_ppm")
    servo_deg = latest_data.get("Servo_deg")
    led_temp_state = latest_data.get("LED_temp")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌡️ Temperatura")
    st.metric("Temperatura (°C)", f"{temp:.1f}" if temp is not None else "—")
    st.subheader("💧 Humedad")
    st.metric("Humedad (%)", f"{hum:.1f}" if hum is not None else "—")

with col2:
    st.subheader("💡 Luz")
    st.metric("Valor luz (ADC)", f"{luz:.0f}" if luz is not None else "—")
    st.subheader("🔥 Gas")
    st.metric("Gas (ppm)", f"{gas_ppm:.0f}" if gas_ppm is not None else "—")

with col3:
    st.subheader("🦾 Servo (válvula)")
    st.metric("Ángulo (°)", f"{servo_deg:.0f}" if servo_deg is not None else "—")
    st.subheader("🌬️ LED temp / ventilador")
    st.write("Estado LED temp:", led_temp_state)

st.markdown("---")

# =============== MENSAJES DE SUGERENCIA ===============
st.header("💡 Sugerencias inteligentes")

if luz is not None:
    if luz < 2000:
        st.info("Luz baja: **te recomiendo encender la lámpara** 💡")
    else:
        st.info("Luz alta: **te recomiendo apagar la lámpara** 😎")

if temp is not None:
    if temp > 30:
        st.warning("Temperatura alta: **te recomiendo encender el ventilador** 🥵")
    elif temp < 22:
        st.success("Temperatura baja: **ventilador innecesario, puedes apagarlo** 🧊")
    else:
        st.info("Temperatura moderada: ventila si lo consideras necesario 😌")

if gas_ppm is not None and gas_ppm > 20000:
    st.error("⚠️ Gas elevado: abre ventanas y revisa la instalación de gas.")

st.markdown("---")

# =============== CONTROL MANUAL DEL VENTILADOR (LED) ===============
st.header("🌬️ Control del ventilador (LED del Wokwi)")

c1, c2 = st.columns(2)
with c1:
    if st.button("Encender ventilador"):
        mqtt_client.publish(MQTT_TOPIC_CMD_VENT, "ON")
        st.success("Comando enviado: encender ventilador")

with c2:
    if st.button("Apagar ventilador"):
        mqtt_client.publish(MQTT_TOPIC_CMD_VENT, "OFF")
        st.success("Comando enviado: apagar ventilador")

st.markdown("---")

# =============== CONTROL POR VOZ DE LA LÁMPARA ===============
st.header("🎙️ Control por voz de la lámpara")

st.write("Di cosas como: **'encender la lámpara'** o **'apagar la lámpara'**")

texto = speech_to_text(
    language="es-ES",
    use_container_width=True,
    just_once=True,
    key="stt_lampara",
)

if texto:
    st.write("➡️ Reconocido:", texto)
    frase = texto.lower()

    encender = any(pal in frase for pal in ["encender", "prender"])
    apagar = "apagar" in frase
    contiene_lampara = any(pal in frase for pal in ["lampara", "lámpara"])

    if contiene_lampara and encender:
        mqtt_client.publish(MQTT_TOPIC_CMD_LAMP, "ON")
        st.success("Comando de voz: **encender lámpara** enviado ✅")
    elif contiene_lampara and apagar:
        mqtt_client.publish(MQTT_TOPIC_CMD_LAMP, "OFF")
        st.success("Comando de voz: **apagar lámpara** enviado ✅")
    else:
        st.warning("No entendí un comando claro para la lámpara 😅")

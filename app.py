import json
import threading
import time

import streamlit as st
import paho.mqtt.client as mqtt

# =============== CONFIG STREAMLIT ===============
st.set_page_config(
    page_title="Entrega Final",
    page_icon="😁",
    layout="wide",
)

st.title("🌿 EcoSense")


# =============== CONFIG MQTT ===============
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC_DATA = "Sensor/THP2"           # datos del ESP32
MQTT_TOPIC_CMD_VENT = "Sensor/cmd/vent"   # comando ventilador (LED_VENT)
MQTT_TOPIC_CMD_LAMP = "Sensor/cmd/lamp"   # comando lámpara (LED_LAMP)

# Últimos datos recibidos
latest_data = {
    "Temp": None,
    "Hum": None,
    "Luz": None,
    "Gas_ppm": None,
    "Servo_deg": None,
    "LED_temp": None,
    "Vent_on": None,
    "Lamp_on": None,
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
                if k in latest_data:
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

# =============== LEER ÚLTIMO JSON ===============
with latest_data_lock:
    temp = latest_data.get("Temp")
    hum = latest_data.get("Hum")
    luz = latest_data.get("Luz")
    gas_ppm = latest_data.get("Gas_ppm")
    servo_deg = latest_data.get("Servo_deg")
    led_temp_state = latest_data.get("LED_temp")
    vent_on = latest_data.get("Vent_on")
    lamp_on = latest_data.get("Lamp_on")

# =============== PANEL DE INDICADORES ===============
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
    st.subheader("🌬️ Ventilador / Lámpara")
    st.write("Ventilador:", "ENCENDIDO" if vent_on else "APAGADO" if vent_on is not None else "—")
    st.write("Lámpara:", "ENCENDIDA" if lamp_on else "APAGADA" if lamp_on is not None else "—")

st.markdown("---")

# =============== SUGERENCIAS ===============
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

# =============== CONTROL MANUAL DEL VENTILADOR ===============
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

# =============== CONTROL MANUAL DE LA LÁMPARA ===============
st.header("💡 Control de la lámpara")

c3, c4 = st.columns(2)
with c3:
    if st.button("Encender lámpara"):
        mqtt_client.publish(MQTT_TOPIC_CMD_LAMP, "ON")
        st.success("Comando enviado: encender lámpara")

with c4:
    if st.button("Apagar lámpara"):
        mqtt_client.publish(MQTT_TOPIC_CMD_LAMP, "OFF")
        st.success("Comando enviado: apagar lámpara")

# =============== AUTO-REFRESH CADA 3 s ===============
time.sleep(3)
st.rerun()




# -*- coding: utf-8 -*-
import os
import json
import time
import cv2
import numpy as np
import board
import busio
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from ai_edge_litert.interpreter import Interpreter

RUTA_MODELO = "modelo_tornillos.tflite"
RUTA_CONFIG = "config_clases.json"
UMBRAL_CONFIANZA = 0.70

ANGULO_REPOSO_EMPUJADOR = 90
ANGULO_EMPUJE_COMPLETO  = 15

USAR_RECORTE = False
ROI_Y1, ROI_Y2 = 80, 400
ROI_X1, ROI_X2 = 160, 480

with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
    config = json.load(f)

CLASES = config["clases"]
ANGULOS_SERVO1 = config["angulos_servo1"]
conteo_piezas = {c: 0 for c in CLASES}
total_clasificadas = 0

PIN_SERVO_1 = 12
PIN_SERVO_2 = 13
PIN_BUZZER  = 18
PIN_BOTON   = 17

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_SERVO_1, GPIO.OUT)
GPIO.setup(PIN_SERVO_2, GPIO.OUT)
GPIO.setup(PIN_BUZZER, GPIO.OUT)
GPIO.setup(PIN_BOTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

pwm1 = GPIO.PWM(PIN_SERVO_1, 50)
pwm2 = GPIO.PWM(PIN_SERVO_2, 50)
pwm1.start(0)
pwm2.start(0)

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

def mostrar_oled(l1, l2="", l3="", l4=""):
    oled.fill(0)
    img = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((2, 2),  l1, font=font, fill=255)
    draw.text((2, 18), l2, font=font, fill=255)
    draw.text((2, 34), l3, font=font, fill=255)
    draw.text((2, 50), l4, font=font, fill=255)
    oled.image(img)
    oled.show()

def mover_servo(pwm, angulo, espera=0.5):
    angulo = max(0, min(180, angulo))
    duty = 2.5 + (angulo / 18.0)
    pwm.ChangeDutyCycle(duty)
    time.sleep(espera)
    pwm.ChangeDutyCycle(0)

def pitar(veces=1, duracion=0.15):
    for _ in range(veces):
        GPIO.output(PIN_BUZZER, GPIO.HIGH)
        time.sleep(duracion)
        GPIO.output(PIN_BUZZER, GPIO.LOW)
        time.sleep(0.08)

mostrar_oled("INICIANDO...", "Cargando modelo", "IA TensorFlow Lite")
interpreter = Interpreter(model_path=RUTA_MODELO)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()[0]
output_details = interpreter.get_output_details()[0]

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def capturar_frame_limpio():
    for _ in range(4):
        cam.read()
    ret, frame = cam.read()
    if not ret:
        return None
    if USAR_RECORTE:
        frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
    return frame

def clasificar_imagen(frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224)).astype(np.float32) / 255.0
    entrada = np.expand_dims(resized, axis=0)

    t0 = time.perf_counter()
    interpreter.set_tensor(input_details["index"], entrada)
    interpreter.invoke()
    latencia_ms = (time.perf_counter() - t0) * 1000.0

    probs = interpreter.get_tensor(output_details["index"])[0]
    idx = int(np.argmax(probs))
    confianza = float(probs[idx])
    return CLASES[idx], confianza, latencia_ms

mover_servo(pwm1, 90)
mover_servo(pwm2, ANGULO_REPOSO_EMPUJADOR)
pitar(2, 0.08)

try:
    while True:
        mostrar_oled(
            "CLASIFICADOR LISTO",
            "Coloque pieza y",
            "pulse el boton...",
            f"Total: {total_clasificadas} piezas"
        )
        print("\n[ESPERANDO] Coloque una pieza y presione el pulsador...")

        while GPIO.input(PIN_BOTON) == GPIO.HIGH:
            time.sleep(0.05)
        time.sleep(0.05)

        mostrar_oled("ANALIZANDO...", "Capturando imagen", "de la estacion...")
        frame = capturar_frame_limpio()
        if frame is None:
            mostrar_oled("ERROR CAMARA", "Verifique conexion", "USB de webcam")
            pitar(3, 0.1)
            time.sleep(2)
            continue

        clase, conf, ms = clasificar_imagen(frame)
        porcentaje = conf * 100.0
        print(f"[RESULTADO] Clase: {clase} | Confianza: {porcentaje:.1f}% | Tiempo: {ms:.1f} ms")

        if conf < UMBRAL_CONFIANZA:
            mostrar_oled(
                "NO RECONOCIDO",
                f"Posible: {clase}",
                f"Conf: {porcentaje:.1f}% (<70%)",
                "Reacomode pieza"
            )
            pitar(3, 0.12)
            time.sleep(2.5)
            continue

        angulo_destino = ANGULOS_SERVO1[clase]
        mostrar_oled(
            "PIEZA DETECTADA:",
            f"> {clase.upper()}",
            f"Confianza: {porcentaje:.1f}%",
            f"Girando a {angulo_destino} deg"
        )

        mover_servo(pwm1, angulo_destino, espera=0.6)
        mover_servo(pwm2, ANGULO_EMPUJE_COMPLETO, espera=0.5)
        mover_servo(pwm2, ANGULO_REPOSO_EMPUJADOR, espera=0.4)

        conteo_piezas[clase] += 1
        total_clasificadas += 1
        pitar(1, 0.25)

        mostrar_oled(
            "CLASIFICADO OK!",
            f"{clase.upper()} -> Caja",
            f"Subtotal {clase[:6]}: {conteo_piezas[clase]}",
            f"Total: {total_clasificadas}"
        )
        time.sleep(1.5)

except KeyboardInterrupt:
    print("\nDeteniendo sistema...")
finally:
    mostrar_oled("SISTEMA APAGADO", "Hasta luego!")
    cam.release()
    pwm1.stop()
    pwm2.stop()
    GPIO.cleanup()
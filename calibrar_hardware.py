# -*- coding: utf-8 -*-
import time
import board
import busio
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# --- CONFIGURACION DE PINES (BCM) ---
PIN_SERVO_1 = 12  # GPIO 12 (Pin 32) - Base Tobogan
PIN_SERVO_2 = 13  # GPIO 13 (Pin 33) - Empujador
PIN_BUZZER  = 18  # GPIO 18 (Pin 12) - Buzzer activo
PIN_BOTON   = 17  # GPIO 17 (Pin 11) - Pulsador NA

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

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
    oled_ok = True
except Exception as e:
    print(f"[AVISO] No se detecto OLED I2C: {e}")
    oled_ok = False

def mostrar_oled(linea1, linea2="", linea3=""):
    if not oled_ok:
        return
    oled.fill(0)
    img = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((2, 5), linea1, font=font, fill=255)
    draw.text((2, 25), linea2, font=font, fill=255)
    draw.text((2, 45), linea3, font=font, fill=255)
    oled.image(img)
    oled.show()

def mover_servo(pwm, angulo):
    angulo = max(0, min(180, angulo))
    duty = 2.5 + (angulo / 18.0)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

def pitar(duracion=0.15):
    GPIO.output(PIN_BUZZER, GPIO.HIGH)
    time.sleep(duracion)
    GPIO.output(PIN_BUZZER, GPIO.LOW)

try:
    print("=== TEST DE HARDWARE INICIADO ===")
    mostrar_oled("TEST HARDWARE", "OLED: OK", "Probando Buzzer...")
    pitar(0.2)
    time.sleep(1)

    print("Centrando Servo 1 y Servo 2 a 90 grados...")
    mostrar_oled("CENTRANDO SERVOS", "Servo 1 -> 90 deg", "Servo 2 -> 90 deg")
    mover_servo(pwm1, 90)
    mover_servo(pwm2, 90)
    time.sleep(1.5)

    angulos_cajas = [20, 55, 90, 125, 160]
    for i, ang in enumerate(angulos_cajas, start=1):
        print(f"Probando Caja {i} -> Servo 1 en {ang} grados")
        mostrar_oled("CALIBRANDO CAJAS", f"Caja {i} / 5", f"Angulo: {ang} deg")
        mover_servo(pwm1, ang)
        pitar(0.08)
        time.sleep(1.2)

    print("Probando Servo 2 (Empujador: 90 -> 15 -> 90 grados)...")
    mostrar_oled("TEST EMPUJADOR", "Avanzando paleta", "y regresando...")
    mover_servo(pwm2, 15)
    time.sleep(0.4)
    mover_servo(pwm2, 90)

    print("\nPresiona el PULSADOR fisico en la protoboard para finalizar...")
    mostrar_oled("PRUEBA BOTON", "Presione el", "pulsador fisico")
    while GPIO.input(PIN_BOTON) == GPIO.HIGH:
        time.sleep(0.05)

    pitar(0.3)
    mostrar_oled("CALIBRACION OK", "Hardware listo", "para despliegue")
    print("Pulsador detectado! Calibracion completada con exito.")

finally:
    pwm1.stop()
    pwm2.stop()
    GPIO.cleanup()
# Clasificador Automático de Tornillería con Visión Artificial

Este proyecto implementa una estación automatizada de clasificación de tornillos, tuercas y arandelas utilizando una Raspberry Pi 4 y visión artificial local con TFLite (TensorFlow Lite). Al presionar un pulsador físico, una cámara captura la pieza en tiempo real, el modelo la identifica en milisegundos y dos servomotores SG90 (alimentados por una fuente externa de 5V) la redirigen hacia su contenedor correspondiente, brindando retroalimentación inmediata mediante una pantalla OLED I2C y un buzzer activo.

El modelo de detección y clasificación fue entrenado utilizando conjuntos de datos públicos disponibles en Roboflow Universe: Screw, Nut, Washer Dataset y Screw Detect Classification Dataset. Para ponerlo en marcha, solo debes clonar el repositorio, activar tu entorno virtual de Python con las dependencias instaladas, verificar las conexiones físicas mediante calibrar_hardware.py y ejecutar main_clasificador.py.

# Sistema Cava AIoT
## Sistema Ciberfísico Autónomo para Cava de Barricas y Crianza de Vinos

### 1. Descripción del proyecto

Este proyecto consiste en el desarrollo de un sistema inteligente para supervisar y controlar las condiciones ambientales de una cava de vinos.

El sistema utiliza sensores para medir temperatura y humedad, almacena los datos en Firebase y permite controlar un extractor de climatización de manera manual y automática.

Además, incorpora un supervisor desarrollado en Python con inteligencia artificial mediante Google Gemini para analizar situaciones de contingencia.

### 2. Objetivos

- Monitorear continuamente la temperatura y humedad.
- Mantener las condiciones ambientales adecuadas para la conservación del vino.
- Permitir el control manual desde un Dashboard web.
- Detectar situaciones ambientales críticas.
- Ejecutar acciones automáticas mediante el ESP32.
- Registrar los análisis y las decisiones del supervisor inteligente.

### 3. Tecnologías utilizadas

- ESP32 DevKit V1.
- Sensor DHT22.
- LED como representación del extractor.
- Wokwi para la simulación electrónica.
- Firebase Realtime Database.
- HTML, CSS y JavaScript.
- Python 3.12.
- FastAPI.
- Google Gemini mediante Google GenAI SDK.

### 4. Estructura del repositorio

```text
Sistema_CAVA_AIOT/
│
├── firmware/
│   ├── sketch.ino
│   ├── diagram.json
│   ├── libraries.txt
│   └── LEER.txt
│
├── frontend/
│   └── cava_dashboard.html
│
├── supervisor_aiot/
│   ├── main.py
│   ├── requirements.txt
│   ├── env.example
│   └── .gitignore
│
└── README.md
```

### 5. Rangos ambientales

| Variable | Rango seguro |
|---|---|
| Temperatura | 12 °C a 18 °C |
| Humedad | 65 % a 80 % |
| Contingencia de temperatura | Superior a 22 °C |
| Contingencia de humedad | Inferior a 60 % |

### 6. Funcionamiento del sistema

1. El sensor DHT22 obtiene las mediciones ambientales.
2. El ESP32 envía los datos a Firebase Realtime Database.
3. El Dashboard web muestra las mediciones en tiempo real.
4. El usuario puede controlar manualmente el extractor.
5. El supervisor Python monitorea las variables ambientales.
6. Ante una contingencia, se realiza un análisis mediante Gemini y se genera una orden de control.
7. El ESP32 recibe las órdenes mediante Server-Sent Events (SSE).
8. El dispositivo ejecuta la acción y envía una confirmación física a Firebase.
9. Cuando las condiciones regresan al rango seguro, el sistema restablece el estado del extractor.

### 7. Instalación y ejecución del supervisor

Se recomienda utilizar Python 3.12.

Crear un entorno virtual:

```bash
py -3.12 -m venv .venv
```

Activarlo en Windows:

```powershell
.venv\Scripts\activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

Configurar las variables de entorno utilizando el archivo `env.example` como referencia.

Crear un archivo `.env` con las credenciales correspondientes:

```env
GEMINI_API_KEY=TU_CLAVE_DE_GEMINI
FIREBASE_DATABASE_URL=TU_URL_DE_FIREBASE
```

Iniciar el servidor:

```bash
python -m uvicorn main:app --reload
```

Acceder a la documentación de la API:

```text
http://127.0.0.1:8000/docs
```

### 8. Simulación

El firmware se ejecuta en Wokwi utilizando un ESP32, un sensor DHT22 y un LED que representa el extractor de climatización.

El archivo `diagram.json` contiene el diseño y las conexiones del circuito.

### 9. Seguridad

- No publicar el archivo `.env`.
- No compartir claves privadas ni credenciales.
- Utilizar reglas de acceso seguras en Firebase.
- Mantener las credenciales fuera del repositorio público.

### 10. Autora

Proyecto académico integrador: Sistema Cava AIoT.

**Sistema Ciberfísico Autónomo para Cava de Barricas y Crianza de Vinos.**

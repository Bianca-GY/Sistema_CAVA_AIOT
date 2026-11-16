import os
import json
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types

# Configuración
load_dotenv(Path(__file__).with_name(".env"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL",
    "https://sistema-cava-aiot-default-rtdb.firebaseio.com"
).rstrip("/")

if not GEMINI_API_KEY:
    raise RuntimeError("Falta GEMINI_API_KEY en supervisor_aiot/.env")

cliente_ia = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supervisor_cava")

RUTA_AMBIENTE = "/bodega/zona_crianza/ambiente.json"
RUTA_ACTUADOR = "/bodega/zona_crianza/actuadores/extractor_estado.json"
RUTA_AUDITORIA = "/bodega/zona_crianza/auditoria_ia.json"

def leer_firebase(ruta):
    r = requests.get(FIREBASE_URL + ruta, timeout=15)
    r.raise_for_status()
    return r.json()

def escribir_firebase(ruta, datos):
    r = requests.put(FIREBASE_URL + ruta, json=datos, timeout=15)
    r.raise_for_status()
    return r.json()

def analizar_ambiente(temperatura, humedad):
    prompt = f"""
Sos un supervisor inteligente de una cava de vinos.
Mediciones: temperatura {temperatura} °C; humedad {humedad} %.
Rangos seguros: temperatura 12-18 °C y humedad 65-80 %.
Contingencias: temperatura superior a 22 °C o humedad inferior a 60 %.
Devolvé exclusivamente JSON válido con:
- alerta_calidad (boolean)
- forzar_climatizacion (boolean)
- impacto_enologico (string en español)
Evaluá el riesgo y explicá brevemente el impacto.
"""
    respuesta = cliente_ia.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    resultado = json.loads(respuesta.text or "{}")
    requeridos = {"alerta_calidad", "forzar_climatizacion", "impacto_enologico"}
    if not requeridos.issubset(resultado):
        raise ValueError("Gemini no devolvió los tres campos requeridos")
    if not isinstance(resultado["alerta_calidad"], bool):
        raise ValueError("alerta_calidad debe ser booleano")
    if not isinstance(resultado["forzar_climatizacion"], bool):
        raise ValueError("forzar_climatizacion debe ser booleano")
    if not isinstance(resultado["impacto_enologico"], str):
        raise ValueError("impacto_enologico debe ser texto")
    return resultado

def supervisar_cava():
    ambiente = leer_firebase(RUTA_AMBIENTE)
    if not isinstance(ambiente, dict) or "temperatura" not in ambiente or "humedad" not in ambiente:
        raise ValueError("Firebase no contiene temperatura y humedad válidas")

    temperatura = float(ambiente["temperatura"])
    humedad = float(ambiente["humedad"])
    if not (0 <= temperatura <= 60 and 0 <= humedad <= 100):
        raise ValueError("Lecturas ambientales fuera de límites físicos plausibles")

    contingencia = temperatura > 22 or humedad < 60
    rango_seguro = 12 <= temperatura <= 18 and 65 <= humedad <= 80

    # Gemini aporta el análisis. Si no está disponible, las reglas locales
    # mantienen la acción de seguridad y registran que hubo fallback.
    try:
        analisis = analizar_ambiente(temperatura, humedad)
        origen_analisis = "Gemini"
    except Exception as error:
        logger.exception("Gemini no respondió; se aplica regla de contingencia")
        analisis = {
            "alerta_calidad": contingencia or not rango_seguro,
            "forzar_climatizacion": contingencia,
            "impacto_enologico": (
                "Análisis automático de respaldo: se detectó una contingencia."
                if contingencia else
                "Análisis de respaldo: revisar condiciones ambientales."
            )
        }
        origen_analisis = "Regla de respaldo (Gemini no disponible)"
        analisis["detalle_error_ia"] = str(error)[:500]

    # Las reglas críticas prevalecen sobre la sugerencia del modelo.
    if contingencia:
        analisis["forzar_climatizacion"] = True
        analisis["alerta_calidad"] = True
    elif rango_seguro:
        analisis["forzar_climatizacion"] = False

    estado = bool(analisis["forzar_climatizacion"])
    escribir_firebase(RUTA_ACTUADOR, estado)

    auditoria = {
        **analisis,
        "temperatura": temperatura,
        "humedad": humedad,
        "modelo_ia": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "origen_analisis": origen_analisis
    }
    escribir_firebase(RUTA_AUDITORIA, auditoria)

    logger.info("Análisis: %s", auditoria)
    logger.info("Orden enviada a Firebase: %s", "ENCENDER" if estado else "APAGAR")
    return {"temperatura": temperatura, "humedad": humedad, **auditoria}

async def monitoreo_automatico():
    logger.info("Monitoreo automático iniciado (cada 5 segundos)")
    contingencia_activa = False
    while True:
        try:
            ambiente = await asyncio.to_thread(leer_firebase, RUTA_AMBIENTE)
            if ambiente:
                temperatura = float(ambiente["temperatura"])
                humedad = float(ambiente["humedad"])
                logger.info("Monitoreo: %.1f °C | %.1f %%", temperatura, humedad)

                contingencia = temperatura > 22 or humedad < 60
                seguro = 12 <= temperatura <= 18 and 65 <= humedad <= 80

                if contingencia and not contingencia_activa:
                    logger.warning("CONTINGENCIA DETECTADA")
                    await asyncio.to_thread(supervisar_cava)
                    contingencia_activa = True
                elif seguro and contingencia_activa:
                    logger.info("Condiciones seguras: restableciendo extractor")
                    await asyncio.to_thread(supervisar_cava)
                    contingencia_activa = False
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error en el monitoreo automático")
        await asyncio.sleep(5)

@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    tarea = asyncio.create_task(monitoreo_automatico())
    try:
        yield
    finally:
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Supervisor Inteligente - Sistema Cava AIoT",
    version="1.0.0",
    lifespan=ciclo_vida
)

@app.get("/")
def inicio():
    return {"mensaje": "Supervisor inteligente de la cava funcionando"}

@app.post("/supervisar")
def ejecutar_supervision():
    try:
        return supervisar_cava()
    except Exception as error:
        logger.exception("Error durante la supervisión")
        raise HTTPException(status_code=500, detail=str(error))

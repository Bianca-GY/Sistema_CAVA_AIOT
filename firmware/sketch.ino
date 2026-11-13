#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "DHT.h"

// Sensor DHT22
#define DHTPIN 4
#define DHTTYPE DHT22

// LED que representa el extractor/climatizador
#define LED_PIN 2

// WiFi de Wokwi
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Firebase Realtime Database
const char* host = "sistema-cava-aiot-default-rtdb.firebaseio.com";
const char* urlAmbiente =
  "https://sistema-cava-aiot-default-rtdb.firebaseio.com/bodega/zona_crianza/ambiente.json";
const char* urlAck =
  "https://sistema-cava-aiot-default-rtdb.firebaseio.com/bodega/zona_crianza/ambiente/extractor_confirmado.json";

// Stream SSE para recibir órdenes sin polling
const char* rutaSSE =
  "/bodega/zona_crianza/actuadores/extractor_estado.json";

DHT dht(DHTPIN, DHTTYPE);
unsigned long tiempoSensor = 0;
const unsigned long intervaloSensor = 5000;
volatile bool estadoLED = false;

void tareaSSE(void* parameter);
void enviarConfirmacion(bool estado);
void enviarTelemetria();

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("Sistema Cava AIoT iniciado");
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi conectado");
  Serial.println(WiFi.localIP());

  xTaskCreatePinnedToCore(
    tareaSSE,
    "TareaSSE",
    8192,
    NULL,
    1,
    NULL,
    0
  );
}

void loop() {
  unsigned long ahora = millis();
  if (ahora - tiempoSensor >= intervaloSensor) {
    tiempoSensor = ahora;
    enviarTelemetria();
  }
  yield();
}

void enviarTelemetria() {
  float humedad = dht.readHumidity();
  float temperatura = dht.readTemperature();

  if (isnan(humedad) || isnan(temperatura)) {
    Serial.println("Error al leer DHT22");
    return;
  }

  Serial.println("--------------------");
  Serial.print("Temperatura: ");
  Serial.println(temperatura);
  Serial.print("Humedad: ");
  Serial.println(humedad);

  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure cliente;
  cliente.setInsecure();  // Solo para simulación educativa en Wokwi
  HTTPClient https;

  if (https.begin(cliente, urlAmbiente)) {
    https.addHeader("Content-Type", "application/json");

    String datos = "{";
    datos += "\"temperatura\":" + String(temperatura, 1) + ",";
    datos += "\"humedad\":" + String(humedad, 1) + ",";
    datos += "\"dispositivo_id\":\"esp32_cava_01\"";
    datos += "}";

    int codigo = https.PATCH(datos);
    Serial.print("Firebase PATCH: ");
    Serial.println(codigo);
    https.end();
  } else {
    Serial.println("Error HTTPS telemetria");
  }
}

void enviarConfirmacion(bool estado) {
  WiFiClientSecure cliente;
  cliente.setInsecure();  // Solo para simulación educativa en Wokwi
  HTTPClient https;

  if (https.begin(cliente, urlAck)) {
    https.addHeader("Content-Type", "application/json");
    int codigo = https.PUT(estado ? "true" : "false");
    Serial.print("Confirmacion fisica PUT: ");
    Serial.println(codigo);
    https.end();
  } else {
    Serial.println("Error al enviar confirmacion");
  }
}

void tareaSSE(void* parameter) {
  while (true) {
    WiFiClientSecure cliente;
    cliente.setInsecure();  // Solo para simulación educativa en Wokwi

    Serial.println("Conectando al Stream SSE...");

    if (cliente.connect(host, 443)) {
      cliente.print(
        String("GET ") + rutaSSE + " HTTP/1.1\r\n" +
        "Host: " + host + "\r\n" +
        "Accept: text/event-stream\r\n" +
        "Cache-Control: no-cache\r\n" +
        "Connection: keep-alive\r\n\r\n"
      );

      // Leer encabezados HTTP
      while (cliente.connected()) {
        String linea = cliente.readStringUntil('\n');
        if (linea == "\r" || linea.length() == 0) break;
      }

      Serial.println("Stream SSE conectado");

      // Escuchar eventos continuamente
      while (cliente.connected()) {
        if (cliente.available()) {
          String linea = cliente.readStringUntil('\n');
          linea.trim();

          if (linea.startsWith("data:")) {
            String contenido = linea.substring(5);
            contenido.trim();

            bool nuevoEstado = estadoLED;
            bool ordenValida = false;

            if (contenido == "true" || contenido.indexOf("\"data\":true") >= 0) {
              nuevoEstado = true;
              ordenValida = true;
            } else if (contenido == "false" || contenido.indexOf("\"data\":false") >= 0) {
              nuevoEstado = false;
              ordenValida = true;
            }

            if (ordenValida && nuevoEstado != estadoLED) {
              estadoLED = nuevoEstado;
              digitalWrite(LED_PIN, estadoLED ? HIGH : LOW);

              Serial.print("Estado enviado al LED: ");
              Serial.println(digitalRead(LED_PIN));
              Serial.print("Orden SSE recibida: ");
              Serial.println(estadoLED ? "ENCENDER" : "APAGAR");

              // Una sola confirmación por cada cambio físico de estado
              enviarConfirmacion(estadoLED);
            }
          }
        } else {
          vTaskDelay(pdMS_TO_TICKS(10));
        }
      }

      Serial.println("Stream SSE desconectado");
    } else {
      Serial.println("Error de conexion SSE");
    }

    cliente.stop();
    Serial.println("Reintentando conexion SSE...");
    vTaskDelay(pdMS_TO_TICKS(2000));
  }
}

# 🛢️ Procesador de Incidentes Ambientales — Oil & Gas Mendoza

Herramienta de extracción y validación de datos desde planillas de incidentes (PDF) de operadoras petroleras.

El proyecto nace con una premisa estricta (Offline-First): operar en hardware legacy de campo con recursos limitados y sin conexión a internet. Para ello, consolida la información en SQLite mediante una interfaz gráfica liviana. A su vez, el motor de extracción está desacoplado, lo que permite exponer los datos vía API Flask para su orquestación y monitoreo automatizado con n8n en entornos corporativos.

**Operadoras soportadas:** YPF S.A. · Pluspetrol S.A. · Petróleos Sudamericanos · Aconcagua Energía · PCR

---

## 🛠 Requisitos
El sistema está diseñado para consumir la menor cantidad de RAM y CPU posible, evitando contenedores pesados (Docker) o frameworks web en el cliente de producción.

-Core: Python 3.10+ y SQLite3 (sin dependencias de red, motor transaccional local).
- Extracción: Expresiones regulares dinámicas (Regex) ajustadas por operadora.

- Frontend (Producción): Interfaz gráfica nativa, optimizada para PCs de escritorio en yacimiento.

- Orquestación (Opcional): Flask (API REST) para gatillar alertas de Data Quality hacia n8n/Telegram.

---
## ⚙️ Modos de Ejecución
El sistema soporta dos modalidades de despliegue según las capacidades del hardware y la red:

A. Modo Producción (Trinchera / Offline)

Es la versión principal utilizada en el día a día. Levanta una interfaz gráfica de usuario (GUI) que permite al operador cargar los PDFs localmente y ver el resultado en pantalla sin depender de internet ni de la línea de comandos.

    python app_incidentes.py

Características: Carga manual de lotes, feedback visual inmediato, validación de coordenadas en memoria y escritura directa en incidentes.db.

B. Modo Integración (API REST + n8n)
Para entornos donde existe conectividad y se busca automatizar el flujo. Levanta un servidor local liviano que permite a herramientas externas consumir los datos y auditar la calidad.
    python api.py

Endpoints principales:
 . GET /errores: Devuelve incidentes que violan las reglas de integridad (ej. coordenadas fuera del Bounding Box de Mendoza). Ideal para conectar con un nodo HTTP de n8n y disparar alertas a Slack/Telegram.
 . GET /status: Health check general.


## 📂 Estructura del Proyecto

```
incidents_processor/
├── data/
│   ├── raw/                  # PDFs a procesar (generados por mock o ingesta real)
│   └── database/             # Base de datos local SQLite (incidentes.db)
├── src/
│   ├── extractors/
│   │   ├── base_extractor.py # Clase base: regex dinámico, fechas, coords
│   │   ├── ypf.py
│   │   ├── pluspetrol.py
│   │   ├── petsud.py
│   │   ├── aconcagua.py
│   │   └── pcr.py
│   ├── transformation/
│   │   └── coordinates.py    # Transformaciones espaciales: WGS84 DD ↔ UTM / Gauss-Krüger
│   └── main.py               # Motor de ejecución CLI (Backend core)
├── tests/
│   ├── conftest.py           # Fixtures con textos sanitizados (mock data) de los PDFs
│   ├── test_base_extractor.py
│   ├── test_extractors.py
│   └── test_coordinates.py
├── logs/                     # Trazabilidad generada automáticamente al ejecutar
├── app_incidentes.py         # Interfaz Gráfica (GUI) - Modo Producción Offline
├── api.py                    # Servidor Flask (API REST) - Modo Integración n8n
├── generate_mock_pdfs.py     # Script generador de PDFs sintéticos para pruebas
├── .env.example              # Plantilla segura para credenciales externas (Tokens/IDs)
├── requirements.txt
└── README.md
```

---

## 🚀 Instalación y Ejecución

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd incidents_processor
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

> **Nota para Linux:** si `pyproj` falla al compilar, instalar primero la librería nativa:
> ```bash
> sudo apt install libproj-dev
> pip install -r requirements.txt
> ```

### 4. Cargar los PDFs

Colocar los archivos PDF de incidentes en la carpeta `data/raw/`:

```
data/raw/
├── Comunicado_N_06-26.pdf
├── Informe_Preliminar_YPF_246524.pdf
└── ...
```

### 5. Ejecutar el procesador

```bash
python src/main.py
```

El proceso imprime el progreso en consola y escribe un log detallado en `logs/processor.log`.

**Salida esperada:**
```
2026-02-19 10:00:00 [INFO] Iniciando proceso. PDFs encontrados: 3
2026-02-19 10:00:01 [INFO] Procesando: Comunicado_N_06-26.pdf
2026-02-19 10:00:01 [INFO] Extractor: PluspetrolExtractor
2026-02-19 10:00:02 [INFO] Procesando: Informe_Preliminar_YPF_246524.pdf
2026-02-19 10:00:02 [INFO] Extractor: YPFExtractor
2026-02-19 10:00:03 [INFO] Proceso finalizado — Insertados: 2 | Omitidos: 0 | Errores: 0
```

### 6. Verificar la base de datos (opcional)

```bash
# Ver registros cargados
sqlite3 data/database/incidentes.db "SELECT NUM_INC, OPERADOR, FECHA_INC, VOL_D_m3 FROM incidentes;"
```

---

## 🧪 Correr los Tests

```bash
# Todos los tests
pytest

# Con reporte de cobertura
pytest --cov=src --cov-report=term-missing

# Solo una operadora
pytest tests/test_extractors.py::TestYPFExtractor -v
```

---

## 📊 Mapeo de Datos y Validación

El sistema normaliza los datos al siguiente esquema unificado:

| Campo | Descripción | Ejemplo |
|---|---|---|
| `NUM_INC` | Identificador único del incidente | `YPF-0000246524` |
| `OPERADOR` | Nombre de la empresa | `YPF S.A.` |
| `AREA_CONCE` | Área concesionada | `CHIHUIDO DE LA SIERRA NEGRA` |
| `FECHA_INC` | Fecha normalizada `dd-mm-yyyy` | `10-10-2025` |
| `Y_COORD` | Latitud WGS84 decimal | `-37.348933` |
| `X_COORD` | Longitud WGS84 decimal | `-69.053400` |
| `COORD_EAST_M` | Este UTM (metros) | `384215.30` |
| `COORD_NORTH_M` | Norte UTM (metros) | `9867043.10` |
| `VOL_D_m3` | Volumen derramado (m³) | `8.5` |
| `VOL_R_m3` | Volumen recuperado (m³) | `1.0` |
| `AGUA_PCT` | Porcentaje de agua | `99.8` |

**Sistemas de coordenadas soportados por operadora:**

| Operadora | Sistema origen | Conversión |
|---|---|---|
| YPF | WGS84 grados decimales | Directa |
| Aconcagua | WGS84 grados decimales | Directa |
| Pluspetrol | WGS84 DD + Gauss-Krüger Faja 2 | Directa |
| Petróleos Sudamericanos | DMS compacto `33°30'57,62"` | DMS → DD |
| PCR | DMS con acento agudo `34°57´51,5"` | DMS → DD |

---

## ⚠️ Reglas de Integridad

1. **Cero duplicados:** el campo `NUM_INC` es único. Si un informe ya fue procesado, el sistema lo ignora silenciosamente.

2. **Consistencia de volúmenes:** se verifica que el volumen recuperado no supere el derramado.

3. **Validación geográfica:** se rechazan registros con coordenadas fuera del bounding box de Mendoza:
   - Latitud: `[-38.0, -32.0]`
   - Longitud: `[-70.0, -67.0]`
   
   Un número mal tipeado que traslade el pozo fuera de la cuenca es detectado y rechazado antes de tocar la base de datos.

4. **Trazabilidad completa:** todos los eventos (inserciones, duplicados, errores, coordenadas inválidas) quedan registrados en `logs/processor.log` con timestamp.

---

## 🧩 Agregar una Nueva Operadora

1. Crear `src/extractors/nueva_operadora.py` heredando de `BaseExtractor`.
2. Implementar el método `extract(self, text) -> dict`.
3. Registrar la operadora en `main.py`:

```python
EXTRACTOR_REGISTRY = [
    ...
    ("PALABRA CLAVE EN PDF", NuevaOperadoraExtractor),
]
```

4. Agregar tests en `tests/test_extractors.py`.

No se necesita modificar ningún otro archivo.

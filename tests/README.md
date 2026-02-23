Tests — Incidents Processor
Suite de tests unitarios y de integración para validar los extractores
y el módulo de transformación de coordenadas.
Estructura
tests/
├── conftest.py           # Fixtures: textos reales extraídos de los PDFs
├── test_base_extractor.py  # Helpers de regex, fechas y coordenadas (BaseExtractor)
├── test_extractors.py      # Tests por operadora (YPF, PetSud, Pluspetrol, Aconcagua, PCR)
└── test_coordinates.py     # Transformación UTM y reglas de dominio geográfico
Cómo correr
bash# Todos los tests
pytest

# Solo una operadora
pytest tests/test_extractors.py::TestYPFExtractor -v

# Solo coordenadas
pytest tests/test_coordinates.py -v

# Con reporte de cobertura (requiere pytest-cov)
pytest --cov=src --cov-report=term-missing
Qué cubre cada archivo
test_base_extractor.py

_find() nunca lanza AttributeError cuando el regex no matchea
_find_float() maneja coma argentina y punto decimal
normalize_date() acepta todos los formatos de fecha del dominio
dms_to_dd() aplica signo correcto por hemisferio
parse_dms_string() maneja los 3 formatos DMS encontrados en los PDFs
validate_coordinates() rechaza puntos fuera del bounding box de Mendoza

test_extractors.py
Cada clase usa el texto real del PDF correspondiente como fixture.
Valida: operador, NUM_INC, área, fecha, coordenadas (signo y valor),
volúmenes y campos específicos de cada formato.
test_coordinates.py

Detección automática de zona UTM
Valores de conversión con tolerancia de ±500m vs referencia externa
Casos borde: None, fuera de rango global, consistencia

Notas

Los fixtures en conftest.py reproducen exactamente el texto extraído
por PyMuPDF de los PDFs originales, sin modificaciones.
El test test_pcr_el_sosneado y test_pluspetrol_jcp_* tienen
tolerancias amplias (±500m) porque sin pyproj instalado se usa
la implementación manual aproximada.
Para máxima precisión en coordenadas: pip install pyproj
CompartirArtefactosDescargar todoEvaluacion codigoCódigo · HTML Contenido
# 🛢️  Industrial Incident Data Pipeline — Oil & Gas (Mendoza Basin)

An automated ETL and data validation engine designed to extract, normalize, and audit environmental incident data from heterogeneous PDF reports in the Energy sector.

This project was built under a strict Offline-First premise: operating on legacy field hardware with limited resources and zero internet connectivity. It consolidates information into a local SQLite database through a lightweight GUI. The extraction engine is decoupled, allowing data exposure via a Flask REST API for orchestration and automated quality monitoring with n8n in corporate cloud environments.

Supported Operators: YPF S.A. · Pluspetrol S.A. · Petróleos Sudamericanos · Aconcagua Energía · PCR.

---

## 🛠 Technical Architecture & Requirements
El sistema está diseñado para consumir la menor cantidad de RAM y CPU posible, evitando contenedores pesados (Docker) o frameworks web en el cliente de producción.
The system is engineered for ultra-low resource consumption (RAM/CPU), avoiding heavy containers or high-overhead web frameworks in production field environments.

Core: Python 3.10+ & SQLite3 (Local transactional engine, zero network dependency).

Data Extraction: Dynamic Regular Expressions (Regex) tailored for non-structured PDF text.

Frontend (Production): Native GUI optimized for legacy desktop environments.

Orchestration (Integration): Flask (REST API) to trigger Data Quality alerts via n8n/Telegram.

---
## ⚙️ Execution Modes
The system supports two deployment modalities based on hardware and network availability:

A. Production Mode (Field / Offline)
The primary daily version. Launches a Graphical User Interface (GUI) allowing operators to load PDFs locally and view results instantly without CLI or internet requirements.

    python app_incidentes.py

Key Features: Batch loading, immediate visual feedback, in-memory coordinate validation, and direct local persistence.

B. Integration Mode (REST API + n8n)
For connected environments requiring automated workflows. Launches a lightweight server for external auditing and data consumption.
    python api.py

Main Endpoints:
 . GET /errors: Returns incidents violating integrity rules (e.g., coordinates outside the Mendoza Bounding Box). Ideal for n8n HTTP nodes to trigger Slack/Telegram alerts.
 . GET /status: General system health check.


##📊 Data Mapping & Deterministic Validation

The system normalizes raw data into a unified, AI-ready schema.
```
Field,Description,Example
NUM_INC,Unique Incident Identifier (Primary Key),YPF-0000246524
OPERADOR,Company Name,YPF S.A.
FECHA_INC,Normalized Date (dd-mm-yyyy),10-10-2025
Y_COORD,WGS84 Decimal Latitude,-37.348933
X_COORD,WGS84 Decimal Longitude,-69.053400
VOL_D_m3,Spilled Volume (m³),8.5
```
⚠️ Integrity Rules (AI-Ready Constraints)

1. Zero Duplicates: NUM_INC is a unique constraint. Re-processed reports are silently ignored to maintain data purity.
2. Geospatial Guardrails: Records with coordinates outside the Mendoza Bounding Box (Lat: [-38.0, -32.0], Lon: [-70.0, -67.0]) are rejected to prevent data entry errors.
3. Volume Consistency: Business logic verification ensuring recovered volume does not exceed spilled volume.
4. Full Traceability: All events (inserts, duplicates, errors) are logged with high-precision timestamps in logs/processor.log.

---
🧪 Testing & Reliability
The project includes a comprehensive test suite with sanitized mock data to ensure logic integrity:
    # Run all tests with coverage report
pytest --cov=src --cov-report=term-missing

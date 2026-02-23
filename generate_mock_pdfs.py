import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Aseguramos que la carpeta exista
output_dir = os.path.join("data", "raw")
os.makedirs(output_dir, exist_ok=True)

# Datos inventados para simular el formato de Pluspetrol
mock_data = [
    {
        "filename": "Comunicado N 01-26.pdf",
        "content": [
            "COMUNICADO N°: 01-26",
            "OPERADOR: Pluspetrol S.A.",
            "FECHA: 15/01/2026",
            "HORA: 14:30",
            "UBICACIÓN ESPECÍFICA: Batería 3 - Zona Sur",
            "CONCESION: El Corcovo",
            "Lat.: -37.1500",
            "Long.: -68.2000",
            "DESCRIPCIÓN:",
            "Durante maniobras de rutina se detectó pérdida.",
            "Vol. derramado: 1.5 m3",
            "Sup. Afectada: 10 m2"
        ]
    },
    {
        "filename": "Comunicado N 02-26_ERROR.pdf",
        "content": [
            "COMUNICADO N°: 02-26",
            "OPERADOR: Pluspetrol S.A.",
            "FECHA: 20/01/2026",
            "Lat.: -41.5000", # Coordenada a propósito fuera de Mendoza
            "Long.: -68.2000",
            "DESCRIPCIÓN:",
            "Derrame menor por falla en válvula.",
            "Vol. derramado: 0.5 m3"
        ]
    }
]

def create_pdf(filename, lines):
    filepath = os.path.join(output_dir, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    y_position = 800
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_position, "Planilla de Comunicación de Accidentes")
    y_position -= 30
    
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(50, y_position, line)
        y_position -= 20
        
    c.save()
    print(f"Generado: {filepath}")

if __name__ == "__main__":
    print("Generando PDFs de prueba...")
    for item in mock_data:
        create_pdf(item["filename"], item["content"])
    print("¡Listo! Ya podés probar el procesador.")
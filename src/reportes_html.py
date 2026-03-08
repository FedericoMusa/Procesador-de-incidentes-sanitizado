def generar_html(stats, incidentes, errores, operadores):
    """Genera un reporte básico para visualizar en el navegador."""
    return f"<html><body><h1>Reporte de Incidentes - Total: {stats['total']}</h1></body></html>"
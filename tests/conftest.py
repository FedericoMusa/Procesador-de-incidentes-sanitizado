"""
Fixtures compartidos para los tests de extractores.
Los textos reproducen exactamente la estructura y formato extraído por PyMuPDF,
pero con datos sintéticos (mock data) para proteger la confidencialidad.
"""

import pytest


@pytest.fixture
def ypf_text():
    return """Res. 24-04 / Dec. 437-93 / Res. 177-10
Comunicado Incidente Nº 0000999999
Informe Preliminar Mendoza
INFORME DEL INCIDENTE
Fecha de ocurrencia: 10/10/2025
Hora de ocurrencia: 10:00
Fecha de alta de registro: 10/10/2025
Operador: YPF S.A.
Unidad económica: NEN - NEGOCIO MOCK
Área operativa: PHM - PTO.MOCK
Yacimiento: YACIMIENTO FICTICIO OESTE
Área concesionada: BLOQUE SIMULADO
Cuenca: NEUQUINA
Provincia: Mendoza
Tipo de permiso: Explotación
Instalación asociada: PLANTA AGUA MOCK
Nombre de la instalación: YPF.NQ.MOCK.A-3 / POZO INYECTOR
Tipo de instalación: CAÑERIA CONDUCCIÓN
Subtipo de instalación: Cañería conducción Agua
Subtipo de incidente: DERRAME DE AGUA DE PRODUCCIÓN
Tipo de evento causante: FALLA DE MATERIALES
Subtipo de evento causante: CORROSION
Magnitud del Incidente: Menor
Descripción: Se observa perdida en linea conducción pozo sumidero MOCK.X-3
INFORMACIÓN GEOGRÁFICA
Grados, minutos y decimales: Latitud (S): 37 ° / 20.000 ' Longitud (W): 69 ° / 3.000 '
Grados, minutos, segundos y decimales: Latitud (S): 37 ° / 20 ' / 00.0 '' Longitud (W): 69 ° / 3 ' / 00.0 ''
Grados y decimales: Latitud (S): 37.333333° Longitud (W): 69.050000°
VOLUMEN
Concentración de hidrocarburo (ppm): menor a 50
Volumen m3 derramado: 8.5000
% Agua contenido: 99.8000
Volumen m3 recuperado: 1.0000
ÁREA AFECTADA
Área m2: 1250.00
Recursos afectados: Suelo, Cauce aluvional
"""


@pytest.fixture
def petsud_text():
    return """N° DE COMUNICADO 999
Fecha de ocurrencia 12/2/2026
Hora de ocurrencia 15:00hs
Operador Petróleos Sudamericanos
Área operativa / concesión Área Ficticia Sur
Yacimiento Punta Mock
Cuenca Cuyana
Provincia Mendoza
Tipo de permiso Explotación
Instalación asociada Acueducto N°9 Mock
Tipo de instalación cañería inyeccion MOCK-191
Subtipo de incidente Crudo
Tipo de evento causante Falla de Materiales - Corrosión
Magnitud del Incidente Menor
Descripción de la rotura y afectación
La perdida se produce en Cañería conduccion MOCK-191, afecta locacion simulada.
Coordenadas x (latitud - S) 33°30'00,00"
Coordenadas y (Longitud - O) 68°38'00,00"
Concentración de hidrocarburo (ppm) Menor a 50ppm
Volumen m3 derramado 7
% AGUA DERRAMADA 100"""
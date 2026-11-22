"""HOGAR_NOMBRE por entorno: obligatoria en producción, con valor de la demo en desarrollo.

Va en config/tests/ porque prueba la configuración del proyecto, no una app: lleva el
marcador infra y se corre sola con -m infra. No usa la base de datos.

Cada caso carga la configuración en un subproceso, con una copia del entorno del test en la que
solo cambian DJANGO_SETTINGS_MODULE y HOGAR_NOMBRE. Recargar el módulo de configuración dentro
de pytest dejaría settings a medias para los demás tests.

"Compose no inventa el nombre del Hogar" no es un test de pytest: se comprueba con
docker compose config en el cierre del cambio.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

# app/, la carpeta de manage.py: desde ahí se importa el paquete config
CARPETA_APP = Path(__file__).resolve().parents[2]
NOMBRE_DEMO = "Hogar Gerontológico Demo"
LEER_HOGAR_NOMBRE = "from django.conf import settings; print(settings.HOGAR_NOMBRE)"


def cargar_configuracion(modulo, hogar_nombre):
    """Carga `modulo` en un subproceso; con hogar_nombre=None, la variable no existe."""
    # Control: el subproceso corre desde la carpeta de manage.py, o no encontraría config
    assert (CARPETA_APP / "manage.py").exists()
    entorno = os.environ.copy()
    entorno["DJANGO_SETTINGS_MODULE"] = modulo
    entorno["PYTHONIOENCODING"] = "utf-8"
    entorno.pop("HOGAR_NOMBRE", None)
    if hogar_nombre is not None:
        entorno["HOGAR_NOMBRE"] = hogar_nombre
    return subprocess.run(
        [sys.executable, "-c", LEER_HOGAR_NOMBRE],
        env=entorno,
        cwd=CARPETA_APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


@pytest.mark.parametrize("hogar_nombre", [None, ""], ids=["ausente", "vacia"])
def test_produccion_sin_hogar_nombre_no_carga(hogar_nombre):
    # Scenario: Producción sin HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)
    resultado = cargar_configuracion("config.settings.prod", hogar_nombre)
    assert resultado.returncode != 0, resultado.stdout
    # La última línea del traceback es la excepción que se lanzó, con su mensaje. Se busca
    # ahí, y no en todo stderr, porque el código del subproceso también nombra HOGAR_NOMBRE.
    ultima_linea = resultado.stderr.strip().splitlines()[-1]
    assert ultima_linea.startswith("django.core.exceptions.ImproperlyConfigured:"), resultado.stderr
    assert "HOGAR_NOMBRE" in ultima_linea
    # No llegó a imprimir un nombre del Hogar
    assert resultado.stdout == ""


def test_produccion_con_hogar_nombre_usa_el_de_la_variable():
    # Scenario: Producción con HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)
    # Regresión: nace en verde, porque base.py ya lee la variable. Es también el control de
    # test_produccion_sin_hogar_nombre_no_carga: en este entorno, config.settings.prod sí
    # carga cuando la variable está definida, así que allá falla solo por HOGAR_NOMBRE.
    resultado = cargar_configuracion("config.settings.prod", "Hogar de prueba")
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "Hogar de prueba"


@pytest.mark.parametrize("hogar_nombre", [None, ""], ids=["ausente", "vacia"])
def test_desarrollo_sin_hogar_nombre_usa_el_de_la_demo(hogar_nombre):
    # Scenario: Desarrollo sin HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)
    # El caso "ausente" es de regresión: ya toma el valor por defecto de base.py. El caso
    # "vacia" protege contra un os.environ.get que deje el nombre del Hogar en "".
    resultado = cargar_configuracion("config.settings.local", hogar_nombre)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == NOMBRE_DEMO

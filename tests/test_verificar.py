"""scripts/verificar.py: qué archivos revisa y cuáles excluye."""

import pytest
import verificar


@pytest.mark.parametrize(
    ("ruta", "excluido"),
    [
        ("templates/base.html", False),
        ("apps/inventario/templates/inventario/existencias.html", False),
        ("staticfiles/admin/x.html", True),
        ("static/vendor/htmx.min.js", True),
        ("apps/x/static/vendor/y.html", True),
        ("htmlcov/index.html", True),
    ],
)
def test_excluye_lo_generado_y_lo_de_terceros(ruta, excluido):
    assert verificar._excluido(ruta) is excluido


def test_solo_revisa_py_y_html_dentro_de_app():
    py, html = verificar._relativas(
        [
            str(verificar.APP / "apps" / "x" / "services.py"),
            str(verificar.APP / "templates" / "base.html"),
            str(verificar.RAIZ / "scripts" / "verificar.py"),
            str(verificar.APP / "static" / "vendor" / "a.html"),
            str(verificar.APP / "docs.md"),
        ]
    )
    assert py == ["apps/x/services.py"]
    assert html == ["templates/base.html"]

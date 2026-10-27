from dashboard.ranking_view import escapar_markdown


def test_escapar_markdown_neutraliza_imagenes_y_enlaces():
    texto = "![x](https://externo/pixel.png) [clic](https://phishing.example)"

    escapado = escapar_markdown(texto)

    assert "![" not in escapado
    assert "](" not in escapado
    assert escapado.replace("\\", "") == texto


def test_escapar_markdown_conserva_texto_plano():
    assert escapar_markdown("Python y SQL") == "Python y SQL"


def test_escapar_markdown_acepta_valores_no_texto():
    assert escapar_markdown(None) == "None"
    assert escapar_markdown(3.5) == "3\.5"


# Sprint 8 - #89: tarjetas del ranking en HTML


def test_tarjeta_candidato_escapa_el_nombre():
    from dashboard.ranking_view import tarjeta_candidato_html

    html_tarjeta = tarjeta_candidato_html(
        1,
        {"email_id": "e1", "puntaje": 75, "confianza_porcentaje": 75},
        '<img src=x onerror="alert(1)">',
    )

    assert "<img" not in html_tarjeta
    assert "&lt;img" in html_tarjeta
    assert "width:75%" in html_tarjeta


def test_tarjeta_candidato_limita_el_puntaje():
    from dashboard.ranking_view import tarjeta_candidato_html

    assert "width:100%" in tarjeta_candidato_html(1, {"puntaje": 250}, "Ana")
    assert "width:0%" in tarjeta_candidato_html(1, {"puntaje": -5}, "Ana")


def test_requisitos_html_escapa_la_evidencia():
    from dashboard.ranking_view import requisitos_html

    resultado = requisitos_html({
        "justificacion": [{"requisito": "SQL", "evidencia": "<script>robar()</script> SQL"}],
        "requisitos_sin_evidencia": ["Power <b>BI</b>"],
    })

    assert "<script>" not in resultado
    assert "&lt;script&gt;" in resultado
    assert "Cumple" in resultado
    assert "Sin evidencia" in resultado
    assert "Power &lt;b&gt;BI&lt;/b&gt;" in resultado


def test_chip_gmail_escapa_la_cuenta():
    from dashboard.gmail_status import chip_estado_gmail

    chip = chip_estado_gmail({"conectado": True, "cuenta": "<b>x</b>@ej.com"})

    assert "<b>x</b>" not in chip
    assert "Gmail conectado" in chip
    assert "tm-chip-ok" in chip

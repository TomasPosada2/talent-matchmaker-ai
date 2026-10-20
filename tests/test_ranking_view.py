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

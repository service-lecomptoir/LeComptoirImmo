"""
Service de génération PDF via Jinja2 + WeasyPrint.
"""
import io
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """Rend un template Jinja2 en HTML."""
    env = _get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def html_to_pdf(html_content: str) -> bytes:
    """Convertit un HTML en PDF via WeasyPrint."""
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_buffer = io.BytesIO()
        WeasyHTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        raise RuntimeError(
            "WeasyPrint n'est pas installé. "
            "Exécutez : pip install weasyprint"
        )


def generate_lease_pdf(lease: Any) -> bytes:
    """Génère le PDF d'un contrat de bail."""
    html = render_template("lease_bail.html.j2", {"lease": lease})
    return html_to_pdf(html)

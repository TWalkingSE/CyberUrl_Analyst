"""
Views package — Módulos de interface Streamlit.
Cada página da aplicação está em seu próprio módulo.
"""

from views.page_dashboard import page_dashboard
from views.page_anatomy import page_anatomy
from views.page_analysis import page_analysis
from views.page_report import page_report
from views.page_quiz import page_quiz
from views.page_scenarios import page_scenarios
from views.page_apis import page_apis
from views.page_datasets import page_datasets
from views.page_settings import page_settings
from views.page_glossary import page_glossary

__all__ = [
    "page_dashboard", "page_anatomy", "page_analysis", "page_report",
    "page_quiz", "page_scenarios", "page_apis", "page_datasets",
    "page_settings", "page_glossary",
]

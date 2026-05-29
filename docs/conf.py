"""Sphinx configuration for djangordf.

``RDFModel``'s metaclass reads Django settings at class-creation time
(``DJANGORDF_DEFAULT_NAMESPACE``, etc.), so we have to call
``django.setup()`` against the test settings module before autodoc
imports anything from the package.
"""
import os
import sys

import django


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _REPO_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()


# -- Project information ----------------------------------------------------

project = "djangordf"
author = "Benjamin Schnabel"
copyright = "2026, Benjamin Schnabel"

try:
    from importlib.metadata import version as _pkg_version
    release = _pkg_version("djangordf")
except Exception:
    release = "0.3.0"
version = ".".join(release.split(".")[:2])


# -- General configuration --------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "superpowers",
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "undoc-members": False,
}

autodoc_typehints = "description"
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
    "django": (
        "https://docs.djangoproject.com/en/stable/",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
}


# -- HTML output ------------------------------------------------------------

html_theme = "furo"
html_title = f"djangordf {release}"

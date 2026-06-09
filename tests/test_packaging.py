"""Regression tests for packaging and import-time settings access.

Both of these tests guard against bugs that bit a downstream user
(the Haskala library) on PyPI 0.4.0:

* ``find_packages(include=['djangordf'])`` silently dropped the
  ``djangordf.backends`` / ``djangordf.management`` subpackages from
  the built wheel, so ``import djangordf`` exploded on a clean install.
* ``RDFModelMeta`` ran ``_build_meta`` for the abstract ``RDFModel``
  base, which accessed Django settings at import time and forced
  every consumer to wire up ``DJANGO_SETTINGS_MODULE`` before they
  could even reach the standalone ``FusekiBackend``.
"""
import os
import subprocess
import sys

from setuptools import find_packages


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_find_packages_includes_every_subpackage():
    """If this assertion ever regresses, the next wheel is broken on PyPI."""
    discovered = set(
        find_packages(where=_REPO_ROOT, include=["djangordf", "djangordf.*"])
    )
    assert discovered == {
        "djangordf",
        "djangordf.backends",
        "djangordf.management",
        "djangordf.management.commands",
    }


def _subprocess_import(code: str) -> subprocess.CompletedProcess:
    """Run ``code`` in a clean subprocess without DJANGO_SETTINGS_MODULE.

    Important to scrub it from the inherited env — the test harness
    sets it (so the rest of the suite can talk to Django) and the
    whole point of this test is to verify imports survive without it.
    """
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_top_level_import_works_without_django_settings():
    result = _subprocess_import("import djangordf")
    assert result.returncode == 0, (
        f"`import djangordf` failed without DJANGO_SETTINGS_MODULE\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_fuseki_backend_import_works_without_django_settings():
    result = _subprocess_import(
        "from djangordf.backends.fuseki import FusekiBackend"
    )
    assert result.returncode == 0, (
        f"`from djangordf.backends.fuseki import FusekiBackend` "
        f"failed without DJANGO_SETTINGS_MODULE\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_rdfmodel_subclass_definable_without_django_settings():
    """Defining a subclass without Django configured used to raise
    ``ImproperlyConfigured`` from inside the metaclass. Now we fall
    through to the ``urn:djangordf:...`` defaults."""
    result = _subprocess_import(
        "from djangordf import RDFModel\n"
        "class Term(RDFModel):\n"
        "    pass\n"
        "assert str(Term._meta.namespace).startswith('urn:djangordf:')\n"
        "assert str(Term._meta.graph_iri).startswith('urn:djangordf:')\n"
    )
    assert result.returncode == 0, (
        f"RDFModel subclass definition failed without DJANGO_SETTINGS_MODULE\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

"""Tests for the lightweight Sentry error filter.

The SDK installs a trace function (``sys.settrace``) that forwards exceptions
originating from ``site-packages/blaxel`` to Sentry. Import errors that happen
because an optional integration extra is not installed (or because a
stripped/partial install is missing the integration's modules) are environment
issues, not SDK defects, and must be filtered out before reaching Sentry.
"""

from blaxel.core.common.sentry import _is_optional_dependency_error


def _raise_in_file(filename: str, code: str) -> Exception:
    """Execute ``code`` as if it lived in ``filename`` and return the exception.

    Using ``compile`` with an explicit filename makes the resulting traceback
    contain a frame whose ``co_filename`` is ``filename``, which lets us simulate
    an error raised from inside a given package path.
    """
    try:
        exec(compile(code, filename, "exec"), {})
    except Exception as e:  # noqa: BLE001 - we want the raised exception object
        return e
    raise AssertionError("code did not raise")


class TestIsOptionalDependencyError:
    """Cover the import-error classification used to suppress Sentry noise."""

    def test_missing_integration_submodule_is_optional(self):
        """The exact production symptom: a stripped install missing model.py.

        ``from .model import *`` in ``blaxel/openai/__init__.py`` raises
        ``ModuleNotFoundError: No module named 'blaxel.openai.model'``.
        """
        exc = ModuleNotFoundError(
            "No module named 'blaxel.openai.model'", name="blaxel.openai.model"
        )
        assert _is_optional_dependency_error(type(exc), exc) is True

    def test_missing_livekit_submodule_is_optional(self):
        exc = ModuleNotFoundError(
            "No module named 'blaxel.livekit.model'", name="blaxel.livekit.model"
        )
        assert _is_optional_dependency_error(type(exc), exc) is True

    def test_each_optional_integration_package_is_covered(self):
        for pkg in (
            "blaxel.langgraph",
            "blaxel.llamaindex",
            "blaxel.openai",
            "blaxel.crewai",
            "blaxel.googleadk",
            "blaxel.livekit",
            "blaxel.pydantic",
            "blaxel.telemetry",
        ):
            exc = ModuleNotFoundError(f"No module named '{pkg}.model'", name=f"{pkg}.model")
            assert _is_optional_dependency_error(type(exc), exc) is True, pkg

    def test_opentelemetry_dependency_is_optional(self):
        """Existing behavior: opentelemetry import errors are still suppressed."""
        exc = ModuleNotFoundError("No module named 'opentelemetry'", name="opentelemetry")
        assert _is_optional_dependency_error(type(exc), exc) is True

    def test_missing_third_party_dep_while_loading_integration_is_optional(self):
        """A missing extra dep (e.g. ``agents`` for blaxel[openai]) is expected."""
        exc = _raise_in_file(
            "/usr/lib/python3.12/site-packages/blaxel/openai/model.py",
            "raise ModuleNotFoundError(\"No module named 'agents'\", name='agents')",
        )
        assert _is_optional_dependency_error(type(exc), exc) is True

    def test_missing_third_party_dep_outside_integration_is_not_optional(self):
        """A third-party import failure outside any optional integration (e.g. a
        genuine missing core dependency) must still be reported."""
        exc = _raise_in_file(
            "/usr/lib/python3.12/site-packages/blaxel/core/common/settings.py",
            "raise ModuleNotFoundError(\"No module named 'httpx'\", name='httpx')",
        )
        assert _is_optional_dependency_error(type(exc), exc) is False

    def test_core_module_import_error_is_not_optional(self):
        """A genuine SDK bug failing on a ``blaxel.*`` core module is captured."""
        exc = ModuleNotFoundError(
            "No module named 'blaxel.core.missing'", name="blaxel.core.missing"
        )
        assert _is_optional_dependency_error(type(exc), exc) is False

    def test_non_import_error_is_not_optional(self):
        exc = ValueError("not an import error")
        assert _is_optional_dependency_error(type(exc), exc) is False

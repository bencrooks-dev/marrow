"""Tracing hooks for agentcore.

A :class:`TraceSink` is a context-manager factory: ``with sink.span(name,
attrs) as span:`` wraps a block of work. Attributes can be added during
the span and the span is closed on exit.

The default implementation is :class:`NullTraceSink` which adds zero
overhead. :class:`PrintTraceSink` is a development helper. The optional
:class:`OpenTelemetryTraceSink` wraps an OpenTelemetry tracer if the
``opentelemetry-api`` package is installed.
"""
from __future__ import annotations

import contextlib
import time
from collections.abc import Iterator, Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Span(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def set_status(self, ok: bool, description: str = "") -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...


@runtime_checkable
class TraceSink(Protocol):
    @contextlib.contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None
    ) -> Iterator[Span]: ...


# --- null + print sinks --------------------------------------------------

class _NullSpan:
    def set_attribute(self, key: str, value: Any) -> None:  # noqa: ARG002
        pass
    def set_status(self, ok: bool, description: str = "") -> None:  # noqa: ARG002
        pass
    def record_exception(self, exc: BaseException) -> None:  # noqa: ARG002
        pass


class NullTraceSink:
    """No-op sink. Zero allocation per span; safe as a default."""

    _NULL_SPAN = _NullSpan()

    @contextlib.contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None,  # noqa: ARG002
    ) -> Iterator[Span]:
        yield self._NULL_SPAN


class _PrintSpan:
    def __init__(self, name: str, start: float) -> None:
        self._name = name
        self._start = start
        self._attrs: dict[str, Any] = {}
        self._ok = True
        self._desc = ""

    def set_attribute(self, key: str, value: Any) -> None:
        self._attrs[key] = value

    def set_status(self, ok: bool, description: str = "") -> None:
        self._ok = ok
        self._desc = description

    def record_exception(self, exc: BaseException) -> None:
        self.set_status(False, f"{type(exc).__name__}: {exc}")


class PrintTraceSink:
    """Prints each completed span to stderr (or any writable)."""

    def __init__(self, file=None) -> None:
        import sys as _s
        self._file = file or _s.stderr

    @contextlib.contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[Span]:
        sp = _PrintSpan(name, time.perf_counter())
        if attributes:
            for k, v in attributes.items():
                sp.set_attribute(k, v)
        try:
            yield sp
        except BaseException as e:
            sp.record_exception(e)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - sp._start) * 1000
            status = "ok" if sp._ok else f"ERR({sp._desc})"
            print(
                f"trace {sp._name} {elapsed_ms:.2f}ms {status} attrs={sp._attrs}",
                file=self._file,
            )


# --- OpenTelemetry adapter ----------------------------------------------

class OpenTelemetryTraceSink:
    """Wraps an OpenTelemetry tracer. Requires opentelemetry-api.

    Usage::

        from opentelemetry import trace
        sink = OpenTelemetryTraceSink(trace.get_tracer("agentcore"))
        runtime = Runtime(trace_sink=sink)
    """

    def __init__(self, tracer) -> None:
        self._tracer = tracer

    @contextlib.contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[Span]:
        with self._tracer.start_as_current_span(name) as otel_span:
            if attributes:
                for k, v in attributes.items():
                    otel_span.set_attribute(k, v)

            class _Adapter:
                def set_attribute(self, key: str, value: Any) -> None:
                    otel_span.set_attribute(key, value)
                def set_status(self, ok: bool, description: str = "") -> None:
                    try:
                        from opentelemetry.trace import Status, StatusCode
                        otel_span.set_status(Status(
                            StatusCode.OK if ok else StatusCode.ERROR,
                            description=description or None,
                        ))
                    except ImportError:
                        pass
                def record_exception(self, exc: BaseException) -> None:
                    otel_span.record_exception(exc)
                    self.set_status(False, str(exc))

            try:
                yield _Adapter()
            except BaseException as e:
                _Adapter().record_exception(e)
                raise


# --- module default ------------------------------------------------------

_default_sink: TraceSink = NullTraceSink()


def set_default_sink(sink: TraceSink) -> None:
    """Install a process-wide default sink. Affects new Runtimes that
    don't supply ``trace_sink`` explicitly."""
    global _default_sink
    _default_sink = sink


def get_default_sink() -> TraceSink:
    return _default_sink

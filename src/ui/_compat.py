from __future__ import annotations


try:
    import streamlit as st
except ImportError:  # pragma: no cover - local fallback without Streamlit
    class _DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __getattr__(self, name):
            def _noop(*args, **kwargs):
                return None

            return _noop

    class _StreamlitStub:
        session_state = {}

        def __getattr__(self, name):
            if name in {"form", "columns"}:
                return self._context_factory

            def _noop(*args, **kwargs):
                if name in {"button", "form_submit_button"}:
                    return False
                if name == "text_input":
                    return kwargs.get("value", "")
                if name == "text_area":
                    return kwargs.get("value", "")
                return None

            return _noop

        def _context_factory(self, *args, **kwargs):
            if args and isinstance(args[0], int):
                return [_DummyContext() for _ in range(args[0])]
            return _DummyContext()

    st = _StreamlitStub()

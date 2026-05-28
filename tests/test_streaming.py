"""Streaming tests — MockProvider should emit multiple chunks."""
from marrow import Agent, MockProvider, Runtime


def test_stream_emits_chunks_and_appends_history():
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider("local")))
    a.append_user("hello there friend")

    chunks: list[str] = []
    final = a.stream(on_chunk=chunks.append)

    assert len(chunks) > 1, "MockProvider should emit at least two chunks"
    assert "".join(chunks) == final
    # Two messages now: user + assistant
    assert a._state.size() == 2


def test_stream_collects_full_text():
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    a.append_user("ping")
    final = a.stream()
    assert "ping" in final
    assert final.startswith("[mock:mock]")


def test_subclassed_python_provider_streams():
    """A Python subclass of Provider can override generate_stream and have
    C++ route into it. This exercises the trampoline."""
    from marrow import GenerationResponse, PyProviderBase

    class FixedProvider(PyProviderBase):
        def name(self):
            return "fixed"

        def generate(self, req):
            r = GenerationResponse()
            r.content = "one two three"
            return r

        def generate_stream(self, req, on_chunk):
            for word in ["one ", "two ", "three"]:
                on_chunk(word)

    rt = Runtime()
    a = rt.add(Agent("a", FixedProvider()))
    a.append_user("ignored")
    chunks: list[str] = []
    final = a.stream(on_chunk=chunks.append)
    assert chunks == ["one ", "two ", "three"]
    assert final == "one two three"

from pathlib import Path

import pytest

from townlight_core.ingest import embedder
from townlight_core.ingest import ingest_bytes, register_handler
from townlight_core.ingest.chunker import chunk_pages
from townlight_core.ingest.parsers import detect_parser


def test_shared_ingest_exports_pdf_parser_and_sentence_chunks() -> None:
    parser = detect_parser(Path("minutes.pdf"))

    assert parser is not None
    assert ".pdf" in parser.supported_extensions

    chunks = chunk_pages(
        [
            {
                "text": (
                    "The council adopted the ordinance. Residents may inspect the "
                    "record at the clerk's office. The effective date is January 1."
                ),
                "page_number": 7,
            }
        ],
        chunk_size=18,
        chunk_overlap=4,
    )

    assert len(chunks) >= 2
    assert chunks[0].page_number == 7
    assert chunks[0].text.endswith("ordinance.")


def test_register_handler_takes_precedence_for_custom_suffix() -> None:
    class CustomParser:
        supported_extensions = [".citycode"]

        def parse(self, file_path: Path):  # pragma: no cover - registry proof only
            raise AssertionError(file_path)

    register_handler(CustomParser())

    from townlight_core.ingest.pipeline import _detect_handler

    assert _detect_handler(Path("longmont.citycode")).__class__.__name__ == "CustomParser"


@pytest.mark.asyncio
async def test_ingest_bytes_uses_ingest_file_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {}

    async def fake_ingest_file(**kwargs):
        calls.update(kwargs)

        class FakeDocument:
            filename = ""
            source_path = ""
            metadata_ = {}

        return FakeDocument()

    async def fake_commit():
        calls["committed"] = True

    monkeypatch.setattr("townlight_core.ingest.pipeline.ingest_file", fake_ingest_file)

    class FakeSession:
        commit = staticmethod(fake_commit)

    doc = await ingest_bytes(
        session=FakeSession(),
        content=b"Longmont code text.",
        filename="longmont.txt",
        source_id="00000000-0000-0000-0000-000000000001",
        source_path="corpus/longmont.txt",
        metadata={"city": "Longmont"},
    )

    assert calls["file_path"].suffix == ".txt"
    assert calls["embed_model"] == "nomic-embed-text"
    assert calls["committed"] is True
    assert doc.filename == "longmont.txt"
    assert doc.source_path == "corpus/longmont.txt"
    assert doc.metadata_["city"] == "Longmont"


@pytest.mark.asyncio
async def test_embed_batch_splits_large_corpus_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    class FakeProvider:
        async def embed_batch(self, texts, *, model):
            calls.append((list(texts), model))
            return [[float(len(text))] for text in texts]

    monkeypatch.setattr(embedder, "_get_provider", lambda base_url="http://localhost:11434": FakeProvider())

    result = await embedder.embed_batch(["a", "bb", "ccc", "dddd", "eeeee"], batch_size=2)

    assert result == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    assert [batch for batch, _model in calls] == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]
    assert {model for _batch, model in calls} == {"nomic-embed-text"}


@pytest.mark.asyncio
async def test_embed_batch_uses_ollama_base_url_env(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_urls = []

    class FakeProvider:
        async def embed_batch(self, texts, *, model):
            return [[1.0] for _text in texts]

    def fake_get_provider(base_url="http://localhost:11434"):
        provider_urls.append(base_url)
        return FakeProvider()

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setattr(embedder, "_get_provider", fake_get_provider)

    await embedder.embed_batch(["records proof"])

    assert provider_urls == ["http://ollama:11434"]

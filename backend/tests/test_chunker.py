from app.rag.chunker import DocumentChunker, PageText


def test_chunker_preserves_pages_and_sequential_metadata() -> None:
    chunker = DocumentChunker(max_chars=200, overlap_chars=45)
    pages = [
        PageText(
            page=3,
            text=(
                "Access control protects company information. "
                "Every collaborator must use an individual account.\n\n"
                "Authentication events are audited and suspicious sessions are revoked. "
                "Passwords must never be shared with another person.\n\n"
                "Managers review access every quarter and report unnecessary permissions."
            ),
        ),
        PageText(page=4, text="Incident response starts by notifying the security team."),
    ]

    chunks = chunker.chunk(pages)

    assert len(chunks) >= 2
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].page == 3
    assert chunks[-1].page == 4
    assert all(chunk.text.strip() for chunk in chunks)


def test_chunker_rejects_zero_based_pages() -> None:
    try:
        PageText(page=0, text="Invalid")
    except ValueError as exc:
        assert str(exc) == "page numbers are one-based"
    else:
        raise AssertionError("zero-based page was accepted")

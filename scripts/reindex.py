"""CLI utility to wipe and rebuild the vector store from files in data/.

Usage:
    python -m scripts.reindex

Run from the project root with the virtual environment activated and
the .env file present.
"""

import sys
from pathlib import Path

# Allow running this script directly (python scripts/reindex.py) by
# ensuring the project root is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import get_settings  # noqa: E402
from app.core.dependencies import get_chroma_service, get_gemini_service  # noqa: E402
from app.core.logging_config import configure_logging, get_logger  # noqa: E402
from app.rag.indexing import IndexingPipeline  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    data_dir = Path(settings.data_dir)
    pdf_files = sorted(data_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{data_dir}'. Nothing to index.")
        return

    gemini_service = get_gemini_service()
    chroma_service = get_chroma_service()
    pipeline = IndexingPipeline(
        gemini_service=gemini_service,
        chroma_service=chroma_service,
        chunk_size_tokens=settings.chunk_size,
        chunk_overlap_tokens=settings.chunk_overlap,
    )

    for pdf_path in pdf_files:
        try:
            pages, chunks = pipeline.index_document(pdf_path, filename=pdf_path.name)
            print(f"Indexed '{pdf_path.name}': {pages} pages, {chunks} chunks.")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to index '{pdf_path.name}': {exc}")


if __name__ == "__main__":
    main()

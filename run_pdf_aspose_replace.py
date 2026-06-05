import sys
import time
import os
import tempfile

import aspose.pdf as ap
import fitz  # PyMuPDF
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider


def build_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_lg"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["fr"])


def placeholder_for_label(label: str) -> str:
    mapping = {
        "PERSON": "<NAME>",
        "PHONE_NUMBER": "<PHONE>",
        "EMAIL_ADDRESS": "<EMAIL>",
        "LOCATION": "<LOCATION>",
        "DATE_TIME": "<DATE>",
    }
    return mapping.get(label, "<REDACTED>")


def extract_pages_text_pymupdf(input_pdf: str) -> list[str]:
    doc = fitz.open(input_pdf)
    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text("text") or "")
    doc.close()
    return pages_text


def split_pdf_into_chunks(input_pdf: str, chunk_size: int = 4) -> list[tuple[str, int]]:
    src = fitz.open(input_pdf)
    total_pages = len(src)
    chunks: list[tuple[str, int]] = []

    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        out = fitz.open()
        out.insert_pdf(src, from_page=start, to_page=end - 1)

        fd, tmp_path = tempfile.mkstemp(prefix="aspose_chunk_", suffix=".pdf")
        os.close(fd)
        out.save(tmp_path)
        out.close()

        chunks.append((tmp_path, start))

    src.close()
    return chunks


def merge_pdfs(inputs: list[str], output_pdf: str) -> None:
    merged = fitz.open()
    for path in inputs:
        part = fitz.open(path)
        merged.insert_pdf(part)
        part.close()
    merged.save(output_pdf)
    merged.close()


def build_entities_per_page(
    pages_text: list[str],
    analyzer: AnalyzerEngine,
) -> list[list[tuple[str, str, int, int]]]:
    entities_per_page: list[list[tuple[str, str, int, int]]] = []

    for text in pages_text:
        if not (text or "").strip():
            entities_per_page.append([])
            continue

        results = analyzer.analyze(text=text, language="fr")
        entities: list[tuple[str, str, int, int]] = []

        for r in results:
            ent_text = (text[r.start : r.end] or "").strip()
            if not ent_text:
                continue

            entities.append((ent_text, r.entity_type, int(r.start), int(r.end)))

        entities.sort(key=lambda x: (x[2], -(len(x[0]))))
        entities_per_page.append(entities)

    return entities_per_page


def replace_text_in_page(page: ap.Page, needle: str, replacement: str) -> int:
    needle = (needle or "").strip()
    if not needle:
        return 0

    txt_absorber = ap.text.TextFragmentAbsorber(needle)
    page.accept(txt_absorber)
    fragments = txt_absorber.text_fragments

    count = 0
    for frag in fragments:
        frag.text = replacement
        count += 1
    return count


def replace_text_in_page_nth(page: ap.Page, needle: str, replacement: str, occurrence_index: int) -> bool:
    needle = (needle or "").strip()
    if not needle:
        return False

    txt_absorber = ap.text.TextFragmentAbsorber(needle)
    page.accept(txt_absorber)
    fragments = list(txt_absorber.text_fragments)
    if occurrence_index < 0 or occurrence_index >= len(fragments):
        return False

    fragments[occurrence_index].text = replacement
    return True


def anonymize_pdf(input_pdf: str, output_pdf: str) -> None:
    analyzer = build_analyzer()
    pages_text_all = extract_pages_text_pymupdf(input_pdf)
    entities_all = build_entities_per_page(pages_text_all, analyzer)

    chunk_paths = split_pdf_into_chunks(input_pdf, chunk_size=4)
    chunk_outputs: list[str] = []

    try:
        for chunk_path, global_start in chunk_paths:
            document = ap.Document(chunk_path)

            max_pages = len(document.pages)
            for local_page_index in range(1, max_pages + 1):
                global_page_index = global_start + local_page_index
                page_entities = entities_all[global_page_index - 1] if global_page_index - 1 < len(entities_all) else []
                if not page_entities:
                    continue

                page = document.pages[local_page_index]

               
                for sample in page_entities[:10]:
                    ent_text, ent_label, start, end = sample

                occurrence_counters: dict[tuple[str, str], int] = {}

                for ent_text, ent_label, start, end in page_entities:
                    if ent_label == "ORGANIZATION":
                        continue

                    replacement = placeholder_for_label(ent_label)
                    key = (ent_text, ent_label)
                    idx = occurrence_counters.get(key, 0)

                    ok = replace_text_in_page_nth(page, ent_text, replacement, idx)
                    if ok:
                       
                        occurrence_counters[key] = idx + 1
                        continue

                    if " " in ent_text:
                        token = ent_text.split()[0]
                        token_key = (token, ent_label)
                        token_idx = occurrence_counters.get(token_key, 0)
                        token_ok = replace_text_in_page_nth(page, token, replacement, token_idx)
                        if token_ok:
                           
                            occurrence_counters[token_key] = token_idx + 1

            fd, tmp_out = tempfile.mkstemp(prefix="aspose_chunk_out_", suffix=".pdf")
            os.close(fd)
            document.save(tmp_out)
            chunk_outputs.append(tmp_out)

        merge_pdfs(chunk_outputs, output_pdf)
    finally:
        for path, _ in chunk_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        for path in chunk_outputs:
            try:
                os.remove(path)
            except OSError:
                pass


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python run_pdf_aspose_replace.py input.pdf output.pdf", file=sys.stderr)
        return 2

    start = time.time()
    anonymize_pdf(argv[1], argv[2])
    end = time.time()

    print(f"PDF anonymisé généré: {argv[2]}")
    print(f"temps {end - start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

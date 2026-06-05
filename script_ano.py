import sys
import time

import fitz  # PyMuPDF
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine


def build_presidio_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {
                "lang_code": "fr",
                "model_name": "fr_core_news_lg",
            }
        ],
    }

    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["fr"],
    )


def anonymize_pdf(input_pdf_path: str, output_pdf_path: str) -> None:
    analyzer = build_presidio_analyzer()
    anonymizer = AnonymizerEngine()

    src = fitz.open(input_pdf_path)
    dst = fitz.open()

    for page_index in range(len(src)):
        page = src[page_index]
        text = page.get_text("text") or ""

        if text.strip():
            results = analyzer.analyze(text=text, language="fr")
            anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
        else:
            anonymized = ""

        rect = page.rect
        new_page = dst.new_page(width=rect.width, height=rect.height)

        if anonymized.strip():
            new_page.insert_textbox(
                rect,
                anonymized,
                fontsize=10,
                fontname="helv",
                align=0,
            )

    dst.save(output_pdf_path)
    dst.close()
    src.close()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python3 script_ano.py input.pdf output.pdf", file=sys.stderr)
        return 2

    start = time.time()
    anonymize_pdf(argv[1], argv[2])
    end = time.time()

    print(f"PDF anonymisé généré: {argv[2]}")
    print(f"temps {end - start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
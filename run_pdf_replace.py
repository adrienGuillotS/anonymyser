import sys
import time

import fitz  # PyMuPDF
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


def build_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_lg"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["fr"])


def build_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


def build_operators() -> dict:
    return {
        "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
        "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
    }


def anonymize_text(text: str, analyzer: AnalyzerEngine, anonymizer: AnonymizerEngine) -> str:
    if not (text or "").strip():
        return ""

    results = analyzer.analyze(text=text, language="fr")
    operators = build_operators()

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )
    return anonymized.text


def anonymize_pdf_replace_text(input_pdf: str, output_pdf: str, fontsize: int = 10) -> None:
    analyzer = build_analyzer()
    anonymizer = build_anonymizer()

    src = fitz.open(input_pdf)
    dst = fitz.open()

    for page_index in range(len(src)):
        page = src[page_index]
        rect = page.rect
        text = page.get_text("text") or ""
        anon_text = anonymize_text(text, analyzer, anonymizer)

        new_page = dst.new_page(width=rect.width, height=rect.height)
        if anon_text.strip():
            new_page.insert_textbox(
                rect,
                anon_text,
                fontsize=fontsize,
                fontname="helv",
                align=0,
            )

    dst.save(output_pdf)
    dst.close()
    src.close()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python run_pdf_replace.py input.pdf output.pdf", file=sys.stderr)
        return 2

    input_pdf = argv[1]
    output_pdf = argv[2]

    start = time.time()
    anonymize_pdf_replace_text(input_pdf, output_pdf)
    end = time.time()

    print(f"PDF anonymisé généré: {output_pdf}")
    print(f"temps {end - start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

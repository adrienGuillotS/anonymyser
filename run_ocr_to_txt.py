import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

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


def build_operators() -> dict:
    return {
        "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
        "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
    }


def presidio_anonymize_text(text: str, analyzer: AnalyzerEngine, anonymizer: AnonymizerEngine) -> str:
    if not (text or "").strip():
        return ""

    results = analyzer.analyze(text=text, language="fr")
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=build_operators(),
    )
    return anonymized.text


def ocr_pdf_to_text(
    input_pdf: str,
    output_txt: str,
    lang: str = "fra",
    dpi: int = 200,
    anonymize: bool = True,
) -> None:
    doc = fitz.open(input_pdf)
    out_path = Path(output_txt)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    analyzer = None
    anonymizer = None
    if anonymize:
        analyzer = build_analyzer()
        anonymizer = AnonymizerEngine()

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    with out_path.open("w", encoding="utf-8") as f:
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang=lang)

            if anonymize and analyzer is not None and anonymizer is not None:
                text = presidio_anonymize_text(text, analyzer, anonymizer)

            f.write(f"--- PAGE {i + 1} ---\n")
            f.write(text.rstrip())
            f.write("\n\n")

    doc.close()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Usage: python run_ocr_to_txt.py input.pdf output.txt [--no-anonymize] [--lang fra] [--dpi 200]",
            file=sys.stderr,
        )
        return 2

    input_pdf = argv[1]
    output_txt = argv[2]

    anonymize = True
    lang = "fra"
    dpi = 200

    i = 3
    while i < len(argv):
        arg = argv[i]
        if arg == "--no-anonymize":
            anonymize = False
            i += 1
            continue
        if arg == "--lang" and i + 1 < len(argv):
            lang = argv[i + 1]
            i += 2
            continue
        if arg == "--dpi" and i + 1 < len(argv):
            dpi = int(argv[i + 1])
            i += 2
            continue

        raise ValueError(f"Unknown argument: {arg}")

    start = time.time()
    ocr_pdf_to_text(input_pdf, output_txt, lang=lang, dpi=dpi, anonymize=anonymize)
    end = time.time()

    print(f"TXT généré: {output_txt}")
    print(f"temps {end - start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

import sys
import time

from run_pdf_replace import anonymize_pdf_replace_text


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python run_pdf_redaction.py input.pdf output.pdf", file=sys.stderr)
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
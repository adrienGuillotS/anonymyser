import fitz  # PyMuPDF
from pathlib import Path
from .base_processor import BaseProcessor


class PdfProcessor(BaseProcessor):
    """
    Processor PDF basé sur annotations de redaction + réécriture d'un placeholder
    dans la zone redacted.
    Chaque page est un bloc de texte.
    """

    def extract_blocks(self, input_path):
        doc = fitz.open(input_path)
        blocks = []
        for page in doc:
            blocks.append(page.get_text("text") or "")
        doc.close()
        return blocks

    def replace_entities(
        self,
        input_path,
        output_path,
        replacements,
        entities_per_block_with_offsets,
        label_to_placeholder=None,
        fontsize=9,
    ):
        if label_to_placeholder is None:
            label_to_placeholder = {
                "PERSON": "<NAME>",
                "EMAIL_ADDRESS": "<EMAIL>",
                "PHONE_NUMBER": "<PHONE>",
                "LOCATION": "<LOCATION>",
                "DATE_TIME": "<DATE>",
                "IBAN_CODE": "<IBAN>",
                "CREDIT_CARD": "<CARD>",
                "URL": "<URL>",
            }

        doc = fitz.open(input_path)

        for page_num, page in enumerate(doc):
            if page_num >= len(entities_per_block_with_offsets):
                break

            entities = entities_per_block_with_offsets[page_num] or []
            if not entities:
                continue

            for ent_text, ent_label, start, end in entities:
                ent_text = (ent_text or "").strip()
                if not ent_text:
                    continue

                placeholder = label_to_placeholder.get(ent_label, "<REDACTED>")

                token_rects = []
                for token in ent_text.split():
                    if not token:
                        continue
                    token_rects.extend(page.search_for(token))

                if not token_rects:
                    continue

                for rect in token_rects:
                    page.add_redact_annot(rect, fill=(1, 1, 1))

            page.apply_redactions()

            for ent_text, ent_label, start, end in entities:
                ent_text = (ent_text or "").strip()
                if not ent_text:
                    continue

                placeholder = label_to_placeholder.get(ent_label, "<REDACTED>")

                first_token = None
                for token in ent_text.split():
                    if token:
                        first_token = token
                        break

                if not first_token:
                    continue

                rects = page.search_for(first_token)
                if not rects:
                    continue

                page.insert_textbox(
                    rects[0],
                    placeholder,
                    fontsize=fontsize,
                    fontname="helv",
                    color=(0, 0, 0),
                    align=1,
                )

        output_dir = Path(output_path).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        doc.save(output_path)
        doc.close()
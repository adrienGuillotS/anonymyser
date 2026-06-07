import os
import sys
import threading
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    base_dir = Path(__file__).resolve().parent

if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

import customtkinter as ctk
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox

from run_docx_replace import anonymize_docx
from run_pdf_aspose_replace import anonymize_pdf as anonymize_pdf_aspose


def _looks_like_scanned_pdf(input_pdf: str, min_chars_per_page: int = 20) -> bool:
    doc = fitz.open(input_pdf)
    try:
        for page in doc:
            text = (page.get_text("text") or "").strip()
            if len(text) >= min_chars_per_page:
                return False
        return True
    finally:
        doc.close()


def _ocr_anonymize_pdf_to_pdf(input_pdf: str, output_pdf: str, dpi: int = 200) -> None:
    try:
        import pytesseract
        from PIL import Image
    except Exception as e:
        raise RuntimeError(
            "OCR requis mais dépendances manquantes. Installe: pytesseract, pillow et tesseract-ocr (système)."
        ) from e

    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_lg"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["fr"])

    anonymizer = AnonymizerEngine()
    operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
        "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
    }

    src = fitz.open(input_pdf)
    dst = fitz.open()

    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_index in range(len(src)):
            page = src[page_index]
            rect = page.rect

            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img, lang="fra")

            results = analyzer.analyze(text=ocr_text, language="fr")
            anon_text = anonymizer.anonymize(
                text=ocr_text,
                analyzer_results=results,
                operators=operators,
            ).text

            new_page = dst.new_page(width=rect.width, height=rect.height)
            if anon_text.strip():
                new_page.insert_textbox(
                    rect,
                    anon_text,
                    fontsize=10,
                    fontname="helv",
                    align=0,
                )

        out_path = Path(output_pdf)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        dst.save(output_pdf)
    finally:
        dst.close()
        src.close()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Anonymiseur")
        self.geometry("920x420")
        self.minsize(860, 380)

        self.file_path = ctk.StringVar(value="")
        self.status = ctk.StringVar(value="Choisis un fichier PDF ou DOCX")

        self._build_ui()
        self._set_working(False)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        root = ctk.CTkFrame(self, corner_radius=18)
        root.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        root.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(header, text="Anonymisation de documents", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="PDF/DOCX → _anonymise (PDF: Aspose replace; fallback OCR si scan)",
            text_color=("#A3A3A3", "#A3A3A3"),
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        card = ctk.CTkFrame(root, corner_radius=18)
        card.grid(row=1, column=0, sticky="nsew", padx=18, pady=10)
        card.grid_columnconfigure(0, weight=1)

        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        path_row.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.file_path, height=42)
        self.path_entry.grid(row=0, column=0, sticky="ew")

        self.browse_btn = ctk.CTkButton(path_row, text="Parcourir", width=140, height=42, command=self._browse)
        self.browse_btn.grid(row=0, column=1, padx=(12, 0))

        self.run_btn = ctk.CTkButton(
            path_row,
            text="Anonymiser",
            width=160,
            height=42,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            command=self._run,
        )
        self.run_btn.grid(row=0, column=2, padx=(12, 0))

        prog_row = ctk.CTkFrame(card, fg_color="transparent")
        prog_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        prog_row.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(prog_row, height=12)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(card, textvariable=self.status, anchor="w")
        self.status_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        tip = ctk.CTkLabel(
            footer,
            text="Tip: sur Windows, installe Tesseract OCR si tu veux le fallback OCR (PDF scannés).",
            text_color=("#A3A3A3", "#A3A3A3"),
            font=ctk.CTkFont(size=11),
        )
        tip.grid(row=0, column=0, sticky="w")

    def _show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def _show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def _set_working(self, working: bool) -> None:
        state = "disabled" if working else "normal"
        self.browse_btn.configure(state=state)
        self.run_btn.configure(state=state)
        self.path_entry.configure(state=state)

        if working:
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.set(0)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir un fichier",
            filetypes=[
                ("Documents", "*.pdf *.docx"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
            ],
        )
        if path:
            self.file_path.set(path)
            self.status.set("Prêt")

    def _run(self) -> None:
        input_path = (self.file_path.get() or "").strip()
        if not input_path:
            self._show_error("Erreur", "Aucun fichier sélectionné")
            return

        ext = Path(input_path).suffix.lower()
        if ext not in {".pdf", ".docx"}:
            self._show_error("Erreur", "Formats supportés: .pdf, .docx")
            return

        output_path = str(Path(input_path).with_name(f"{Path(input_path).stem}_anonymise{ext}"))

        self._set_working(True)
        self.status.set("Traitement en cours...")

        def worker() -> None:
            try:
                if ext == ".docx":
                    anonymize_docx(input_path, output_path)
                else:
                    if _looks_like_scanned_pdf(input_path):
                        self._ui_status("PDF scanné détecté → OCR + anonymisation...")
                        _ocr_anonymize_pdf_to_pdf(input_path, output_path)
                    else:
                        anonymize_pdf_aspose(input_path, output_path)

                self._ui_done(output_path)
            except Exception as e:
                self._ui_error(str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _ui_status(self, msg: str) -> None:
        self.after(0, lambda: self.status.set(msg))

    def _ui_done(self, output_path: str) -> None:
        def cb() -> None:
            self._set_working(False)
            self.status.set(f"Terminé: {output_path}")
            self._show_info("OK", f"Fichier créé:\n{output_path}")

        self.after(0, cb)

    def _ui_error(self, msg: str) -> None:
        def cb() -> None:
            self._set_working(False)
            self.status.set("Erreur")
            self._show_error("Erreur", msg)

        self.after(0, cb)


def main() -> None:
    os.environ.setdefault("CUSTOMTKINTER_DEFAULT_COLOR_THEME", "blue")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

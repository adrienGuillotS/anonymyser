import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path

import fitz  # PyMuPDF

from run_docx_replace import anonymize_docx
from run_pdf_aspose_replace import anonymize_pdf as anonymize_pdf_aspose
from presidio_anonymizer import AnonymizerEngine

from run_ocr_to_txt import build_analyzer, build_operators


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

    analyzer = build_analyzer()
    anonymizer = AnonymizerEngine()
    operators = build_operators()

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


class AnonymizerApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=16)
        self.master = master
        self.file_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Sélectionne un fichier PDF ou DOCX")

        self._build_ui()
        self._set_working(False)

    def _build_ui(self) -> None:
        self.master.title("Anonymiseur")
        self.master.minsize(760, 320)

        style = ttk.Style(self.master)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        bg = "#0B1220"
        card_bg = "#111B2E"
        fg = "#E5E7EB"
        muted = "#9CA3AF"
        accent = "#4F46E5"

        self.master.configure(background=bg)
        style.configure("App.TFrame", background=bg)
        style.configure("Card.TFrame", background=card_bg)
        style.configure("Title.TLabel", background=card_bg, foreground=fg, font=("Helvetica", 18, "bold"))
        style.configure("Subtitle.TLabel", background=card_bg, foreground=muted, font=("Helvetica", 11))
        style.configure("Status.TLabel", background=card_bg, foreground=muted, font=("Helvetica", 10))
        style.configure("TEntry", fieldbackground="#0F172A", foreground=fg)
        style.configure("Primary.TButton", background=accent, foreground="#FFFFFF", padding=(14, 10))
        style.map("Primary.TButton", background=[("active", "#4338CA"), ("disabled", "#3730A3")])
        style.configure("Secondary.TButton", background="#1F2937", foreground=fg, padding=(14, 10))
        style.map("Secondary.TButton", background=[("active", "#111827")])
        style.configure("TProgressbar", thickness=8)

        container = ttk.Frame(self, style="App.TFrame")
        container.grid(row=0, column=0, sticky="nsew")

        card = ttk.Frame(container, style="Card.TFrame", padding=20)
        card.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(card, text="Anonymisation de documents", style="Title.TLabel")
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        subtitle = ttk.Label(card, text="PDF/DOCX → fichier _anonymise", style="Subtitle.TLabel")
        subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 16))

        entry = ttk.Entry(card, textvariable=self.file_path_var)
        entry.grid(row=2, column=0, sticky="ew")

        browse = ttk.Button(card, text="Parcourir", style="Secondary.TButton", command=self._browse)
        browse.grid(row=2, column=1, padx=(10, 0))

        run = ttk.Button(card, text="Anonymiser", style="Primary.TButton", command=self._run)
        run.grid(row=2, column=2, padx=(10, 0))

        self.progress = ttk.Progressbar(card, mode="indeterminate")
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(16, 8))

        status = ttk.Label(card, textvariable=self.status_var, style="Status.TLabel")
        status.grid(row=4, column=0, columnspan=3, sticky="w")

        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        card.columnconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._browse_btn = browse
        self._run_btn = run

    def _set_working(self, working: bool) -> None:
        if working:
            self._browse_btn.state(["disabled"])
            self._run_btn.state(["disabled"])
            self.progress.start(10)
        else:
            self._browse_btn.state(["!disabled"])
            self._run_btn.state(["!disabled"])
            self.progress.stop()

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
            self.file_path_var.set(path)
            self.status_var.set("Prêt")

    def _run(self) -> None:
        input_path = self.file_path_var.get().strip()
        if not input_path:
            messagebox.showerror("Erreur", "Aucun fichier sélectionné")
            return

        ext = Path(input_path).suffix.lower()
        if ext not in {".pdf", ".docx"}:
            messagebox.showerror("Erreur", "Formats supportés: .pdf, .docx")
            return

        output_path = str(Path(input_path).with_name(f"{Path(input_path).stem}_anonymise{ext}"))

        self._set_working(True)
        self.status_var.set("Traitement en cours...")

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
        self.master.after(0, lambda: self.status_var.set(msg))

    def _ui_done(self, output_path: str) -> None:
        def cb() -> None:
            self._set_working(False)
            self.status_var.set(f"Terminé: {output_path}")
            messagebox.showinfo("OK", f"Fichier créé:\n{output_path}")

        self.master.after(0, cb)

    def _ui_error(self, msg: str) -> None:
        def cb() -> None:
            self._set_working(False)
            self.status_var.set("Erreur")
            messagebox.showerror("Erreur", msg)

        self.master.after(0, cb)


def main() -> None:
    root = tk.Tk()
    app = AnonymizerApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

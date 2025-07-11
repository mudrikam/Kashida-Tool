"""
Gemini AI Integration for Arabic Typing Helper
"""

from PySide6.QtWidgets import QInputDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
import qtawesome as qta
from gemini_ai_helper import request_gemini
from gemini_response_helper import parse_gemini_response

import json
import re

class GeminiWorker(QThread):
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
    
    def run(self):
        try:
            response = request_gemini(self.prompt)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class GeminiIntegration:
    def __init__(self, parent):
        self.parent = parent
        self.worker = None
        self.progress_dialog = None

    def create_progress_dialog(self, title, message):
        progress = QProgressDialog(message, "Batal", 0, 0, self.parent)
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.setMinimumDuration(0)
        progress.setWindowIcon(qta.icon('fa6s.star', color='deepskyblue'))
        progress.show()
        return progress

    def show_gemini_dialog(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self.parent, "Gemini Sibuk", "Gemini sedang memproses. Mohon tunggu.")
            return
        
        options = [
            "Tulis ulang dalam Arab",
            "Perbaiki (ejaan/harakat)",
            "Cek kesalahan",
            "Auto harakat",
            "Prompt bebas",
            "Cari ayat",
            "Cari hadith"
        ]
        
        dlg = QInputDialog(self.parent)
        dlg.setWindowTitle("AI Gemini")
        dlg.setLabelText("Pilih aksi:")
        dlg.setComboBoxItems(options)
        dlg.setWindowIcon(qta.icon('fa6s.star', color='deepskyblue'))
        dlg.setComboBoxEditable(False)
        
        ok = dlg.exec()
        choice = dlg.textValue()
        if not ok:
            return
        
        prompt = self.build_prompt(choice)
        if not prompt:
            return
        
        self.execute_gemini_request(prompt, choice)

    def build_prompt(self, choice):
        user_text = self.parent.text_area.toPlainText()
        catatan_instruksi = (
            'Tambahkan field "catatan" yang berisi peringatan crosscheck hasil AI dengan sumber Al-Qur\'an/hadith sahih atau bertanya ke ustadz/guru. '
            'CATATAN HARUS SINGKAT, JELAS, DAN TIDAK LEBIH DARI 1 KALIMAT. '
            'JANGAN isi catatan dengan penjelasan ayat/hadith/konten. '
            'Catatan WAJIB berupa peringatan crosscheck, HARUS berbeda-beda (variatif), dan sebutkan bahwa hasil ini dari AI. '
            'JANGAN menyalin contoh literal apapun, gunakan variasi kalimat peringatan crosscheck.'
        )
        penjelasan_instruksi = (
            'Tambahkan field "penjelasan" yang berisi penjelasan singkat dan relevan sesuai konteks permintaan user. '
            'Penjelasan boleh berupa tafsir, konteks, atau makna tambahan, maksimal 2 kalimat.'
        )
        
        if choice == "Tulis ulang dalam Arab":
            return f"""Tuliskan ulang kalimat berikut dalam huruf Arab dengan harakat yang benar.
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan. {catatan_instruksi} {penjelasan_instruksi}

{{
  "result": "teks arab dengan harakat yang benar",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": ""
}}

Teks input: {user_text}"""
        
        elif choice == "Perbaiki (ejaan/harakat)":
            return f"""Perbaiki ejaan dan harakat pada teks Arab berikut.
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan. {catatan_instruksi} {penjelasan_instruksi}

{{
  "result": "teks arab yang sudah diperbaiki",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": ""
}}

Teks input: {user_text}"""
        
        elif choice == "Cek kesalahan":
            return f"""Cek dan perbaiki kesalahan pada teks Arab berikut.
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan. {catatan_instruksi} {penjelasan_instruksi}

{{
  "result": "teks arab yang sudah diperbaiki",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": ""
}}

Teks input: {user_text}"""
        
        elif choice == "Auto harakat":
            return f"""Tambahkan harakat yang benar pada teks Arab berikut.
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan. {catatan_instruksi} {penjelasan_instruksi}

{{
  "result": "teks arab dengan harakat lengkap",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": ""
}}

Teks input: {user_text}"""
        
        elif choice == "Prompt bebas":
            return self.get_custom_prompt_with_note(catatan_instruksi + " " + penjelasan_instruksi)
        
        elif choice == "Cari ayat":
            return self.get_ayat_prompt(catatan_instruksi + " " + penjelasan_instruksi)
        
        elif choice == "Cari hadith":
            return self.get_hadith_prompt(catatan_instruksi + " " + penjelasan_instruksi)
        
        return None

    def get_custom_prompt_with_note(self, instruksi):
        custom_dlg = QInputDialog(self.parent)
        custom_dlg.setWindowTitle("Prompt Bebas")
        custom_dlg.setLabelText("Masukkan prompt Gemini:")
        custom_dlg.setWindowIcon(qta.icon('fa6s.comment-dots', color='green'))
        ok = custom_dlg.exec()
        custom_prompt = custom_dlg.textValue()
        if not ok or not custom_prompt.strip():
            return None
        return f"""{custom_prompt.strip()}

Jawab HANYA dalam format JSON dan {instruksi}"""

    def get_ayat_prompt(self, instruksi):
        context_dlg = QInputDialog(self.parent)
        context_dlg.setWindowTitle("Cari Ayat")
        context_dlg.setLabelText("Masukkan konteks, topik, atau tema ayat (boleh dikosongkan jika tahu surah/ayat):")
        context_dlg.setWindowIcon(qta.icon('fa6s.lightbulb', color='gold'))
        ok_context = context_dlg.exec()
        context = context_dlg.textValue().strip() if ok_context else ""
        
        surah_dlg = QInputDialog(self.parent)
        surah_dlg.setWindowTitle("Cari Ayat")
        surah_dlg.setLabelText("Masukkan nomor surah (1-114) atau nama surah (boleh dikosongkan):")
        surah_dlg.setWindowIcon(qta.icon('fa6s.book-open', color='orange'))
        ok_surah = surah_dlg.exec()
        surah = surah_dlg.textValue().strip() if ok_surah else ""
        
        ayat_dlg = QInputDialog(self.parent)
        ayat_dlg.setWindowTitle("Cari Ayat")
        ayat_dlg.setLabelText("Masukkan nomor ayat (atau rentang, misal 1-5, boleh dikosongkan):")
        ayat_dlg.setWindowIcon(qta.icon('fa6s.book-open', color='orange'))
        ok_ayat = ayat_dlg.exec()
        ayat = ayat_dlg.textValue().strip() if ok_ayat else ""
        
        options = ["Ya", "Tidak"]
        
        arti_dlg = QInputDialog(self.parent)
        arti_dlg.setWindowTitle("Opsi Ayat")
        arti_dlg.setLabelText("Sertakan arti?")
        arti_dlg.setComboBoxItems(options)
        arti_dlg.setWindowIcon(qta.icon('fa6s.language', color='green'))
        ok_arti = arti_dlg.exec()
        sertakan_arti = arti_dlg.textValue()
        if not ok_arti:
            return None
        
        baca_dlg = QInputDialog(self.parent)
        baca_dlg.setWindowTitle("Opsi Ayat")
        baca_dlg.setLabelText("Sertakan cara baca (latin)?")
        baca_dlg.setComboBoxItems(options)
        baca_dlg.setWindowIcon(qta.icon('fa6s.microphone', color='purple'))
        ok_baca = baca_dlg.exec()
        sertakan_cara_baca = baca_dlg.textValue()
        if not ok_baca:
            return None
        
        asbab_dlg = QInputDialog(self.parent)
        asbab_dlg.setWindowTitle("Opsi Ayat")
        asbab_dlg.setLabelText("Sertakan asbabun nuzul?")
        asbab_dlg.setComboBoxItems(options)
        asbab_dlg.setWindowIcon(qta.icon('fa6s.clock-rotate-left', color='brown'))
        ok_asbab = asbab_dlg.exec()
        sertakan_asbab = asbab_dlg.textValue()
        if not ok_asbab:
            return None

        note_instruction = instruksi

        if (not surah and not ayat) and context:
            prompt = f"""Carikan ayat Al-Qur'an yang relevan dengan topik atau konteks berikut: "{context}".
Tampilkan ayat Arab lengkap dengan harakat.
Pada hasil JSON, field "sumber" WAJIB diisi dengan format: Nama Surah: Nomor Ayat. Jika tidak tahu pasti, tuliskan sumber ayat sebisa mungkin.
JANGAN menyalin atau mencontohkan format literal apapun, selalu isi field "sumber" dengan sumber ayat yang benar sesuai hasil pencarian.
{note_instruction}"""
            if sertakan_arti == "Ya":
                prompt += "\nSertakan juga artinya dalam bahasa Indonesia."
            if sertakan_cara_baca == "Ya":
                prompt += "\nSertakan juga cara bacanya (latin/transliterasi)."
            if sertakan_asbab == "Ya":
                prompt += "\nSertakan juga asbabun nuzul jika tersedia."
            prompt += """
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan:

{
  "result": "teks ayat arab dengan harakat",
  "arti": "arti ayat (jika diminta)",
  "cara_baca": "cara baca latin (jika diminta)",
  "asbabun_nuzul": "asbabun nuzul (jika diminta)",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": "",
  "sumber": "Nama Surah: Nomor Ayat"
}"""
            return prompt

        prompt = f"""Tulis ayat Al-Qur'an"""
        if surah:
            prompt += f" surah {surah}"
        if ayat:
            prompt += f" ayat {ayat}"
        prompt += " dalam huruf Arab lengkap dengan harakat."
        prompt += "\nPada hasil JSON, field \"sumber\" WAJIB diisi dengan format: Nama Surah: Nomor Ayat. Jika tidak tahu pasti, tuliskan sumber ayat sebisa mungkin."
        prompt += "\nJANGAN menyalin atau mencontohkan format literal apapun, selalu isi field \"sumber\" dengan sumber ayat yang benar sesuai hasil pencarian."
        prompt += f"\n{note_instruction}"
        if sertakan_arti == "Ya":
            prompt += "\nSertakan juga artinya dalam bahasa Indonesia."
        if sertakan_cara_baca == "Ya":
            prompt += "\nSertakan juga cara bacanya (latin/transliterasi)."
        if sertakan_asbab == "Ya":
            prompt += "\nSertakan juga asbabun nuzul jika tersedia."
        if context:
            prompt += f"\nJika memungkinkan, prioritaskan ayat yang relevan dengan konteks/topik berikut: \"{context}\"."
        prompt += """
Jawab HANYA dalam format JSON berikut, tanpa penjelasan tambahan:

{
  "result": "teks ayat arab dengan harakat",
  "arti": "arti ayat (jika diminta)",
  "cara_baca": "cara baca latin (jika diminta)",
  "asbabun_nuzul": "asbabun nuzul (jika diminta)",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": "",
  "sumber": "Nama Surah: Nomor Ayat"
}"""
        return prompt

    def get_hadith_prompt(self, catatan_instruksi):
        topik_dlg = QInputDialog(self.parent)
        topik_dlg.setWindowTitle("Cari Hadith")
        topik_dlg.setLabelText("Masukkan topik, konteks, atau kata kunci hadith:")
        topik_dlg.setWindowIcon(qta.icon('fa6s.book-bookmark', color='purple'))
        ok_topik = topik_dlg.exec()
        topik = topik_dlg.textValue()
        if not ok_topik or not topik.strip():
            return None
        
        return """Carikan hadith sahih yang berkaitan dengan topik: "{}"

PENTING: 
- HANYA tampilkan hadith yang benar-benar SAHIH dari Bukhari, Muslim, atau koleksi sahih lainnya
- Jika hadith diragukan atau tidak sahih, berikan peringatan jelas
- Jika tidak menemukan hadith sahih tentang topik ini, katakan dengan jujur
- Sertakan sumber yang jelas (nama kitab, nomor hadith)
- {} Tambahkan field "penjelasan" yang berisi penjelasan singkat dan relevan sesuai konteks permintaan user. Penjelasan boleh berupa makna, konteks, atau ringkasan hadith, maksimal 2 kalimat. Catatan tetap hanya untuk peringatan crosscheck.

Jawab HANYA dalam format JSON berikut:

{{
  "result": "teks hadith dalam bahasa Arab (jika ada)",
  "hadith_text": "terjemahan hadith dalam bahasa Indonesia",
  "hadith_source": "sumber hadith (kitab, nomor, perawi)",
  "hadith_warning": "peringatan jika hadith diragukan atau saran untuk cross-check ke ustadz/guru (jika perlu)",
  "penjelasan": "penjelasan singkat sesuai konteks (maksimal 2 kalimat)",
  "catatan": "",
  "sumber": "Nama Kitab: Nomor Hadith"
}}

Topik: {}""".format(topik, catatan_instruksi, topik)

    def execute_gemini_request(self, prompt, choice):
        self.progress_dialog = self.create_progress_dialog("AI Gemini", f"Memproses permintaan: {choice}...")
        self.progress_dialog.canceled.connect(self.on_progress_cancelled)
        
        self.worker = GeminiWorker(prompt)
        self.worker.finished.connect(self.on_gemini_finished)
        self.worker.error.connect(self.on_gemini_error)
        self.worker.start()

    def on_gemini_finished(self, response):
        print("=== RAW GEMINI RESPONSE ===")
        print(response)
        print("==========================")
        
        self.progress_dialog.close()
        self.progress_dialog = None

        main_text, catatan = self.extract_main_and_catatan(response)
        main_text = re.sub(r'(\n+)[\.\•]+\s*', r'\1', main_text)
        main_text = re.sub(r'^[\.\•]+\s*', '', main_text)
        self.parent.text_area.setPlainText(main_text)
        self.parent.show_catatan(catatan)
        
        self.worker = None

    def extract_main_and_catatan(self, response):
        if not response:
            return "", ""
        try:
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = None
            if not json_str:
                # Cari inline JSON
                json_inline = re.search(r'(\{.*?\})', response, re.DOTALL)
                if json_inline:
                    json_str = json_inline.group(1)
            if json_str:
                obj = json.loads(json_str)
                # Parse and order fields correctly with penjelasan included
                fields = [
                    ("result", False),
                    ("cara_baca", False),
                    ("arti", False),
                    ("asbabun_nuzul", False),
                    ("hadith_text", False),
                    ("hadith_source", False),
                    ("hadith_warning", True),
                    ("penjelasan", False)
                ]
                lines = []
                for key, is_warning in fields:
                    value = obj.get(key)
                    if value and key != "sumber":
                        if is_warning:
                            lines.append("⚠️ " + str(value))
                        else:
                            lines.append(str(value))
                # Always add sumber at the end if it exists
                sumber = obj.get("sumber") or ""
                if sumber:
                    lines.append(str(sumber))
                main_text = "\n\n".join(lines).strip()
                catatan = obj.get("catatan") or obj.get("note") or ""
                return main_text, catatan
        except Exception:
            pass
        # Jika gagal, fallback ke parser lama
        parsed = parse_gemini_response(response)
        # Cari catatan dengan regex
        catatan_match = re.search(r'(catatan|note)[\s:"]+(.+)', response, re.IGNORECASE)
        catatan = catatan_match.group(2).strip() if catatan_match else ""
        return parsed, catatan

    def on_gemini_error(self, error_message):
        """Handle Gemini error"""
        self.progress_dialog.close()
        self.progress_dialog = None
        QMessageBox.critical(self.parent, "Kesalahan Gemini", f"Kesalahan: {error_message}")
        self.worker = None

    def on_progress_cancelled(self):
        """Handle progress dialog cancellation"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        self.worker = None

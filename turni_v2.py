import sys
import calendar
import datetime
import os
import json
import copy
import shutil
import time
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QMarginsF, QRectF
from PySide6.QtGui import QShortcut, QKeySequence, QPen
from PySide6.QtGui import QPainter, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtGui import QColor, QBrush, QFont, QCursor, QFontMetricsF
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                               QMenu, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QInputDialog, QWidget, QVBoxLayout,
                               QComboBox, QSpinBox, QDialog, QListWidget, QListWidgetItem, QHBoxLayout,
                               QPushButton, QDialogButtonBox, QLabel, QTextBrowser)

APP_VERSION = "2.0"
ABOUT_HTML = f"""
<h2>Moreno</h2>
<p><b>Pianificatore turni medici</b><br>U.O.C. di Anestesia e Rianimazione</p>
<p>Versione {APP_VERSION}</p>
<p>Sviluppato da <b>Ill.mo Software</b></p>
<p>&copy; 2026 Ill.mo Software. Tutti i diritti riservati.</p>
<p style="font-size:small">I dati sono salvati solo sul tuo computer (o chiavetta), nella cartella del programma.
Il software &egrave; fornito &laquo;cos&igrave; com'&egrave;&raquo;, senza garanzie di alcun tipo.
Verifica sempre i turni prima della stampa e della pubblicazione.</p>
<p style="font-size:small">Realizzato con Python e Qt (PySide6).<br>Include turno mensile, turno settimanale e stampa PDF.</p>
<p style="font-size:small"><i>Made with Moreno &copy;</i></p>
"""

MANUAL_HTML = """
<h2>Manuale rapido</h2>
<h3>Inserire i turni</h3>
<ul>
<li>Ogni medico ha due met\u00e0 per giorno: <b>in alto mattina</b>, <b>in basso pomeriggio</b>.</li>
<li><b>Clic</b> su una casella: appare l'elenco dei turni possibili. "Altro" permette una sigla libera.</li>
<li><b>Tasto destro</b> su un turno: elimina il turno o aggiungi/rimuovi il gettone (#).</li>
<li>Ferie, L.104, Mal, Agg: dopo il primo giorno scegli "-" (continua) oppure trascina il mouse verso destra sui giorni successivi.</li>
<li>Clic sulla riga grigia: aggiunge una nota al giorno (es. "Bimbi").</li>
<li>Clic sull'intestazione di un giorno: imposta o rimuove un <b>festivo locale</b>.</li>
</ul>
<h3>Sigle e ore</h3>
<ul>
<li>Mattina da sola 7 h; pomeriggio sempre 6 h; mattina + pomeriggio 12 h; guardie (RG, AG, RN, AN) 12 h.</li>
<li>F, L.104, Agg, Mal contano 6h20 (0 h di domenica e nei festivi); "/" (riposo) 0 h.</li>
<li>Il gettone (#) toglie 6 h su un turno singolo, 12 h su una guardia. Obiettivo mensile: 152 h.</li>
</ul>
<h3>Regole automatiche</h3>
<ul>
<li>RM, RG, RN, U, AG e AGP non possono essere assegnati a due medici lo stesso giorno (nel menu appare il nome di chi li ha gi\u00e0).</li>
<li>Dopo una notte (RN/AN) il giorno dopo si possono scegliere solo "/", RN, AN.</li>
</ul>
<h3>Controlli</h3>
<ul>
<li><b>Controlla copertura</b>: elenca i giorni in cui manca una guardia. Il simbolo \u26a0 compare anche sull'intestazione del giorno.</li>
<li>Lun-ven servono RM, RG, RN, U, AGP, pi\u00f9 TA al mattino e P al pomeriggio. Sabato, domenica e festivi servono RG, RN, AG.</li>
<li><b>Riepilogo</b>: per ogni medico guardie, festivi, gettoni, assenze, ore e differenza dalle 152 h.</li>
<li><b>Medici</b>: aggiungi, rinomina, rimuovi o sposta i medici (vale per tutti i mesi).</li>
</ul>
<h3>Turno settimanale</h3>
<ul>
<li>Il pulsante <b>Settimanale</b> apre la settimana (luned\u00ec-domenica) con guardie, ambulatori e sale operatorie, mattina e pomeriggio.</li>
<li>Le sale (SO al mattino, SOP al pomeriggio) si compilano da sole in base ai turni del mese; i medici si possono cambiare dal menu a scomparsa. Cliccando sul giorno in alto scegli, per mattina e pomeriggio, quali specialit\u00e0 sono attive (anche entrambe); il valore predefinito \u00e8 lo schema abituale.</li>
<li>Un "?" rosso indica una guardia obbligatoria mancante: con un clic puoi confermare che resta scoperta ("/").</li>
<li>Nel fine settimana il medico AG 12 ore compare sia al mattino sia al pomeriggio.</li>
<li><b>Tasto destro</b> su una casella: "Modifica a mano..." per forzare qualsiasi valore (un nome per riga, "-" per svuotare) oppure "Ripristina valore automatico". Le caselle forzate sono sottolineate.</li>
<li>Puoi ripristinare l'assegnazione automatica o svuotare tutte le sale; c'\u00e8 anche l'ambulatorio TA del pomeriggio.</li>
<li><b>Esporta PDF</b>: pagina A4 orizzontale pronta da stampare. I dati settimanali sono salvati in "turni_settimane.json".</li>
</ul>
<h3>Colori delle sigle</h3>
<ul>
<li>Rosso: RG, RM, RN, AG, AGP, AN, U. Blu: TA. Verde: SO, SOP. Viola: P. Nero: tutte le altre. Gli stessi colori valgono nel PDF.</li>
</ul>
<h3>Salvataggio e stampa</h3>
<ul>
<li>Il salvataggio \u00e8 automatico. Ogni mese ha il proprio file; le copie di sicurezza sono nella cartella "backup".</li>
<li><b>Annulla (Ctrl+Z)</b> annulla l'ultima modifica.</li>
<li><b>Esporta PDF</b>: pagina A3 orizzontale con la legenda; tutte le sigle hanno la stessa dimensione.</li>
<li>I file si trovano nella stessa cartella del programma: per spostare i dati basta copiare la cartella.</li>
</ul>
"""

YEAR, MONTH = datetime.date.today().year, datetime.date.today().month
TARGET = 152 * 60
DOCTORS = ["Momesso", "Coppo", "De Bernardo", "Deghaili", "Di Mari", "Licciardello",
           "Santagati", "Shyti", "Vidal", "Souto Valadares", "",
           "Andreetta", "De Nobili", "De Paris", "Di Caro", "Ferrante", "Fonda",
           "Gulino", "Gismondo", "Lacava", "Lucca", "Marzolini", "Michelutto",
           "Piacente", "Randazzo", "Khudjakof"]

DAY_GUARD = {"RG": 12, "AG": 12}
NIGHT_GUARD = {"RN": 12, "AN": 12}
MORNING = {"RM": 7, "U": 7, "SO": 7, "TA": 7}
AFTERNOON = {"SOP": 6, "P": 6, "AGP": 6}
PM_CODES = {*AFTERNOON, "TA"}
FERIE = "F"
BLOCK = ("F", "L.104", "Agg", "Mal", "/")
MERGED = ("RG", "AG", "RN", "AN", "F", "L.104", "Mal", "Agg", "/")
CONTINUABLE = ("F", "L.104", "Mal", "Agg")
GETTONE_H = 6 * 60
FULL = {**DAY_GUARD, **NIGHT_GUARD}
HOURS = {k: v * 60 for k, v in {**FULL, **MORNING, **AFTERNOON, }.items()}
for k in BLOCK:
    HOURS[k] = 6 * 60 + 20
HOURS["/"] = 0
CUSTOM = "__custom__"
NO_SUNDAY = ("F", "L.104", "Agg", "Mal")


def day_hours(code, d):
    if code in NO_SUNDAY and is_red(d):
        return 0
    return HOURS.get(code, 0)


def fmt(m):
    return f"{m // 60}.{m % 60:02d}"

UNIQUE = ("RM", "RG", "RN", "AN", "U", "AG", "AGP")
REQUIRED_WEEKDAY_ONLY = ("RM", "U", "AGP")
REQUIRED_OFFDAY_ONLY = ("AG",)
WD = ["LU", "MA", "ME", "GIO", "VE", "SA", "DO"]
MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio",
        "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
COL_NAME, COL_FIRST = 0, 1
NDAYS = COL_TOT = 0
CUSTOM_HOL = {}


def set_month(y, m):
    global YEAR, MONTH, NDAYS, COL_TOT
    YEAR, MONTH = y, m
    NDAYS = calendar.monthrange(y, m)[1]
    COL_TOT = NDAYS + 1
    CUSTOM_HOL.clear()


set_month(YEAR, MONTH)
WEEKEND = QColor("#ffffa6")
SEPARATOR = QColor("#dddddd")
RED, GREEN, BLUE, PURPLE = QColor("#e00000"), QColor("#00a000"), QColor("#0000ff"), QColor("#9000c0")
TEXT_COLORS = {**{k: RED for k in ("RG", "RM", "RN", "AG", "AGP", "AN", "U")},
               **{k: GREEN for k in ("SO", "SOP")},
               "P": PURPLE, "TA": BLUE}


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    j, k = c // 4, c % 4
    m = (a + 11 * h) // 319
    r = (2 * e + 2 * j - k - h + m + 32) % 7
    mese = (h - m + r + 90) // 25
    giorno = (h - m + r + mese + 19) % 32
    return datetime.date(y, mese, giorno)


def holidays(y):
    fixed = {(1, 1): "Capodanno", (1, 6): "Epifania", (4, 25): "Liberazione",
             (5, 1): "Festa del Lavoro", (6, 2): "Festa della Repubblica",
             (8, 15): "Ferragosto", (11, 1): "Ognissanti", (12, 8): "Immacolata",
             (12, 25): "Natale", (12, 26): "Santo Stefano"}
    pas = easter(y)
    fixed[(pas.month, pas.day)] = "Pasqua"
    lun = pas + datetime.timedelta(days=1)
    fixed[(lun.month, lun.day)] = "Lunedì dell'Angelo"
    return fixed


def holiday_name(d):
    return holidays(YEAR).get((MONTH, d)) or CUSTOM_HOL.get(d)


def is_red(d):
    return datetime.date(YEAR, MONTH, d).weekday() == 6 or holiday_name(d) is not None


def save_file():
    return os.path.join(base_dir(), f"turni_{YEAR}_{MONTH:02d}.json")


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def doctors_file():
    return os.path.join(base_dir(), "medici.json")


def load_doctors():
    try:
        with open(doctors_file(), encoding="utf-8") as f:
            lst = json.load(f)
        if isinstance(lst, list) and lst.count("") == 1 and all(isinstance(x, str) for x in lst):
            DOCTORS[:] = lst
    except (OSError, ValueError):
        pass


load_doctors()

BACKUP_EVERY = 600
BACKUP_KEEP = 30
_last_backup = {}


def backup(path, force=False):
    """Copia datata del file in backup\\, al massimo una ogni 10 minuti (salvo force)."""
    if not os.path.exists(path):
        return
    now = time.time()
    if not force and now - _last_backup.get(path, 0) < BACKUP_EVERY:
        return
    _last_backup[path] = now
    folder = os.path.join(os.path.dirname(path), "backup")
    os.makedirs(folder, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    shutil.copy2(path, os.path.join(folder, f"{stem}_{time.strftime('%Y%m%d_%H%M%S')}.json"))
    old = sorted(f for f in os.listdir(folder) if f.startswith(stem + "_"))
    for f in old[:-BACKUP_KEEP]:
        os.remove(os.path.join(folder, f))


class Planner(QTableWidget):
    def __init__(self):
        super().__init__(len(DOCTORS) * 2, NDAYS + 2)
        self.data = {}
        self.notes = {}
        self.undo_stack = []
        self.sep_row = None
        self.ready = False
        self.footer = None
        self.drag_start = None
        self.hover = None
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.open_menu)
        self.setMouseTracking(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.cellEntered.connect(self.on_enter)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(20)
        self.setColumnWidth(COL_NAME, 130)
        for c in range(COL_FIRST, COL_TOT):
            self.setColumnWidth(c, 48)
        self.setColumnWidth(COL_TOT, 70)
        heads = ["Medico"]
        for d in range(1, NDAYS + 1):
            heads.append(f"{WD[datetime.date(YEAR, MONTH, d).weekday()]}\n{d}")
        heads.append("Ore")
        self.setHorizontalHeaderLabels(heads)
        self.style_headers()
        self.horizontalHeader().sectionClicked.connect(self.header_menu)
        for i, name in enumerate(DOCTORS):
            r = i * 2
            for rr in (r, r + 1):
                for c in range(self.columnCount()):
                    it = QTableWidgetItem("")
                    it.setTextAlignment(Qt.AlignCenter)
                    self.setItem(rr, c, it)
            self.setSpan(r, COL_NAME, 2, 1)
            self.setSpan(r, COL_TOT, 2, 1)
            self.item(r, COL_NAME).setText(name)
            self.item(r, COL_NAME).setFont(QFont("Segoe UI", 9, QFont.Bold))
            if not name:
                for rr in (r, r + 1):
                    for c in range(self.columnCount()):
                        self.item(rr, c).setBackground(QBrush(SEPARATOR))
                    self.setRowHeight(rr, 10)
                for d in range(1, NDAYS + 1):
                    self.setSpan(r, COL_FIRST + d - 1, 2, 1)
                    self.item(r, COL_FIRST + d - 1).setFont(QFont("Segoe UI", 6))
                self.sep_row = r
                continue
            self.refresh_row(i)

    def missing_coverage(self):
        present = {}
        for (i, dd), e in self.data.items():
            present.setdefault(dd, set()).update(c for c in (e.get("m"), e.get("p")) if c)
        res = {}
        for d in range(1, NDAYS + 1):
            off = datetime.date(YEAR, MONTH, d).weekday() >= 5 or is_red(d)
            have = present.get(d, set())
            miss = [c for c in UNIQUE if c not in have
                    and not (off and c in REQUIRED_WEEKDAY_ONLY)
                    and not (not off and c in REQUIRED_OFFDAY_ONLY)]
            if not off:
                if not any(e.get("m") == "TA" for (i, dd), e in self.data.items() if dd == d):
                    miss.append("TA mattina")
                if not any(e.get("p") == "P" for (i, dd), e in self.data.items() if dd == d):
                    miss.append("P pomeriggio")
            if miss:
                res[d] = miss
        return res

    def style_headers(self):
        miss = self.missing_coverage()
        for d in range(1, NDAYS + 1):
            h = self.horizontalHeaderItem(COL_FIRST + d - 1)
            h.setText(f"{WD[datetime.date(YEAR, MONTH, d).weekday()]}\n{d}" + (" \u26a0" if d in miss else ""))
            h.setForeground(QBrush(QColor("#e00000") if is_red(d) else QColor("black")))
            tip = holiday_name(d) or ""
            if d in miss:
                tip += ("\n" if tip else "") + "Manca: " + ", ".join(miss[d])
            h.setToolTip(tip)

    def header_menu(self, col):
        if not (COL_FIRST <= col < COL_TOT):
            return
        d = col - COL_FIRST + 1
        national = holidays(YEAR).get((MONTH, d))
        menu = QMenu(self)
        a_add = menu.addAction("Segna come festivo...")
        a_add.setEnabled(not national)
        a_del = menu.addAction("Rimuovi festivo locale")
        a_del.setEnabled(d in CUSTOM_HOL)
        act = menu.exec(QCursor.pos())
        if act is None:
            return
        self.push_undo()
        if act is a_add:
            text, ok = QInputDialog.getText(self, "Festivo locale", "Nome (es. Santo patrono):",
                                            text=CUSTOM_HOL.get(d, ""))
            if not ok:
                self.undo_stack.pop()
                return
            CUSTOM_HOL[d] = text.strip() or "Festivo locale"
        else:
            CUSTOM_HOL.pop(d, None)
        self.refresh_holidays()

    def refresh_holidays(self):
        self.style_headers()
        for i, name in enumerate(DOCTORS):
            if name:
                self.refresh_row(i)
        self.update_counters()
        self.save()

    def refresh_notes(self):
        if self.sep_row is None:
            return
        for d in range(1, NDAYS + 1):
            it = self.item(self.sep_row, COL_FIRST + d - 1)
            it.setText(self.notes.get(d, ""))
            it.setToolTip(self.notes.get(d, ""))

    def note_menu(self, d, pos):
        menu = QMenu(self)
        menu.addAction("Bimbi").setData("Bimbi")
        menu.addAction("Altra nota...").setData(CUSTOM)
        a_del = menu.addAction("Elimina nota")
        a_del.setEnabled(d in self.notes)
        act = menu.exec(pos)
        if act is None:
            return
        self.push_undo()
        if act is a_del:
            self.notes.pop(d, None)
        else:
            text = act.data()
            if text == CUSTOM:
                text, ok = QInputDialog.getText(self, "Nota", "Nota:", text=self.notes.get(d, ""))
                text = text.strip()
                if not ok:
                    return
            if text:
                self.notes[d] = text
            else:
                self.notes.pop(d, None)
        self.refresh_notes()
        if self.ready:
            self.save()

    def export_pdf(self, path):
        w = QPdfWriter(path)
        w.setPageSize(QPageSize(QPageSize.A3))
        w.setPageOrientation(QPageLayout.Landscape)
        w.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
        w.setResolution(150)
        p = QPainter(w)
        W, H = p.device().width(), p.device().height()
        n = sum(1 for x in DOCTORS if x)
        title_h, head_h = 60, 70
        half = min(44, (H - title_h - head_h - 10 - 26 * 6 - 44) / (2 * n + 1))
        unit = W / (NDAYS + 2.6)
        xs = [0, unit * 2.6]
        for _ in range(NDAYS):
            xs.append(xs[-1] + unit)
        p.setPen(Qt.black)
        f = QFont("Segoe UI", 16, QFont.Bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, W, title_h), Qt.AlignLeft | Qt.AlignVCenter,
                   f"U.O.C. di Anestesia e Rianimazione - {MESI[MONTH - 1].upper()} {YEAR}")

        def cell(c, y, h, text, color=None, fg=Qt.black, maxpt=12, top=False, frame=True):
            r = QRectF(xs[c], y, xs[c + 1] - xs[c], h)
            if frame:
                if color:
                    p.fillRect(r, color)
                p.drawRect(r)
            font = QFont("Segoe UI", maxpt, QFont.Bold)
            lines = text.split("\n") or [""]
            while font.pointSizeF() > 5:
                fm = QFontMetricsF(font, p.device())
                if (max(fm.horizontalAdvance(s) for s in lines) <= r.width() - 6
                        and fm.height() * 0.85 * len(lines) <= r.height() - 2):
                    break
                font.setPointSizeF(font.pointSizeF() - 0.5)
            p.setFont(font)
            p.setPen(fg)
            p.drawText(r, (Qt.AlignHCenter | Qt.AlignTop) if top else Qt.AlignCenter, text)
            p.setPen(Qt.black)

        uni = 12.0
        cw, hh = xs[2] - xs[1], half
        for i, name in enumerate(DOCTORS):
            if not name:
                continue
            for k in (0, 1):
                for d in range(1, NDAYS + 1):
                    t = self.item(i * 2 + k, COL_FIRST + d - 1).text()
                    if not t:
                        continue
                    h_av = hh * 2 if self.entry(i, d).get("m") in MERGED else hh
                    fnt = QFont("Segoe UI", 12, QFont.Bold)
                    while fnt.pointSizeF() > 5:
                        fm = QFontMetricsF(fnt, p.device())
                        if (fm.horizontalAdvance(t) <= cw - 6
                                and fm.height() * 0.85 <= h_av - 2):
                            break
                        fnt.setPointSizeF(fnt.pointSizeF() - 0.5)
                    uni = min(uni, fnt.pointSizeF())
        y = title_h
        cell(0, y, head_h, "Medico", maxpt=14)
        for d in range(1, NDAYS + 1):
            col = WEEKEND if self.weekend(d) else None
            cell(d, y, head_h, f"{WD[datetime.date(YEAR, MONTH, d).weekday()]}\n{d}", col,
                 QColor("#e00000") if is_red(d) else Qt.black, 12)
        y += head_h
        for i, name in enumerate(DOCTORS):
            if not name:
                p.fillRect(QRectF(0, y, xs[-1], half), SEPARATOR)
                for d, text in self.notes.items():
                    cell(d, y, half, text, SEPARATOR, maxpt=10)
                y += half
                continue
            r = i * 2
            cell(0, y, half * 2, name, maxpt=14)
            for d in range(1, NDAYS + 1):
                if self.entry(i, d).get("m") in MERGED:
                    it = self.item(r, COL_FIRST + d - 1)
                    cell(d, y, half * 2, it.text(), it.background().color(), it.foreground().color(), uni, True)
                    continue
                e = self.entry(i, d)
                for k in (0, 1):
                    it = self.item(r + k, COL_FIRST + d - 1)
                    p.fillRect(QRectF(xs[d], y + k * half, xs[d + 1] - xs[d], half), it.background().color())
                cell(d, y, half * 2, "")
                for k in (0, 1):
                    it = self.item(r + k, COL_FIRST + d - 1)
                    cell(d, y + k * half, half, it.text(), None, it.foreground().color(), uni, True, False)
            y += half * 2
        y += 20
        red, green, blue, purple = QColor("#e00000"), QColor("#00a000"), QColor("#0000e0"), QColor("#9000c0")
        legend = [
            [("RG", "GUARDIA RIANIMAZIONE GIORNO (8-20)", red), ("AG mat", "GUARDIA ANESTESIA MATTINA (8-15)", red), ("P", "AMBULATORIO ANESTESIA (14-20)", purple)],
            [("RM", "GUARDIA RIANIMAZIONE MATTINA (8-15)", red), ("AGP", "GUARDIA ANESTESIA POMERIGGIO (14-20)", red), ("TA", "TERAPIA ANTALGICA (8-15)", blue)],
            [("RN", "GUARDIA RIANIMAZIONE NOTTE (20-8)", red), ("AN", "GUARDIA ANESTESIA NOTTE (20-8)", red), ("#", "\u201cGETTONE\u201d", Qt.black)],
            [("U", "URGENTISTA (8-15)", red), ("SO", "SALA OPERATORIA (8-15)", green), ("F", "FERIE      (-) = continuo di ferie", Qt.black)],
            [("AG", "GUARDIA ANESTESIA (8-20)", red), ("SOP", "SALA OPERATORIA POMERIGGIO (14-20)", green), None],
        ]
        lh = 26
        fr = [0, .05, .30, .36, .62, .67, 1.0]
        lx = [W * v for v in fr]

        def lbox(x0, x1, yy, hh, text, color, bold=True, center=False):
            rr = QRectF(x0, yy, x1 - x0, hh)
            p.setPen(Qt.black)
            p.drawRect(rr)
            font = QFont("Segoe UI", 10, QFont.Bold if bold else QFont.Normal)
            while font.pointSizeF() > 5 and QFontMetricsF(font, p.device()).horizontalAdvance(text) > rr.width() - 8:
                font.setPointSizeF(font.pointSizeF() - 0.5)
            p.setFont(font)
            p.setPen(color)
            p.drawText(rr.adjusted(4, 0, -4, 0), (Qt.AlignHCenter if center else Qt.AlignLeft) | Qt.AlignVCenter, text)

        for row in legend:
            for g, item in enumerate(row):
                code, desc, col = item if item else ("", "", Qt.black)
                lbox(lx[g * 2], lx[g * 2 + 1], y, lh, code, col, True, True)
                lbox(lx[g * 2 + 1], lx[g * 2 + 2], y, lh, desc, col, code != "F")
            y += lh
        lbox(0, W, y, lh, "LE CASELLE DIVISE IN 2 SIGNIFICA: in alto MATTINA \u2013 in basso POMERIGGIO       -------       "
             "SE C\u2019E\u2019 SOLO LA CASELLA SOTTO:  E\u2019 solo il turno di POMERIGGIO       -------       "
             "LE CASELLE BIANCHE SIGNIFICANO RIPOSO/RECUPERO", Qt.black, True, True)
        p.setPen(Qt.black)
        p.setFont(QFont("Segoe UI", 8, QFont.Normal, True))
        p.drawText(QRectF(0, y + lh + 2, W, 20), Qt.AlignRight | Qt.AlignTop, "Made with Moreno \u00a9")
        p.end()

    def weekend(self, d):
        return datetime.date(YEAR, MONTH, d).weekday() >= 5 or holiday_name(d) is not None

    def entry(self, i, d):
        return self.data.get((i, d), {})

    def after_night(self, i, d):
        return d > 1 and self.entry(i, d - 1).get("m") in NIGHT_GUARD

    def options(self, i, d, half):
        e = self.entry(i, d)
        if self.after_night(i, d):
            return [] if e else ["/", *NIGHT_GUARD]
        if half == "m" and e.get("m") in MORNING and "p" not in e:
            return [c for c in (*AFTERNOON, "TA") if not (self.weekend(d) and c in REQUIRED_WEEKDAY_ONLY)]
        if e.get("m") in FULL or e.get("m") in BLOCK or half in e:
            return []
        opts = list(MORNING) if half == "m" else [*AFTERNOON, "TA"]
        if not e:
            opts += list(DAY_GUARD) + list(NIGHT_GUARD) + list(BLOCK)
            if d > 1 and self.entry(i, d - 1).get("m") in CONTINUABLE:
                opts.insert(0, "-")
        if self.weekend(d):
            opts = [o for o in opts if o not in REQUIRED_WEEKDAY_ONLY]
        else:
            opts = [o for o in opts if o not in REQUIRED_OFFDAY_ONLY]
        return opts

    def calc_row(self, i):
        total = ngett = 0
        for d in range(1, NDAYS + 1):
            e = self.entry(i, d)
            merged = e.get("m") in MERGED
            if e.get("m") in FULL or e.get("m") in BLOCK:
                total += day_hours(e["m"], d)
            else:
                m, pm = e.get("m"), e.get("p")
                mh = HOURS.get(m, 0)
                if pm in PM_CODES:
                    ph = 6 * 60
                    if m in MORNING:
                        mh = 6 * 60
                else:
                    ph = HOURS.get(pm, 0)
                total += mh + ph
            ng = len(e.get("g", ()))
            if merged:
                ng = min(ng, 1)
            ngett += ng
            total -= ng * (HOURS[e["m"]] if merged else GETTONE_H)
        return total, ngett

    def refresh_row(self, i):
        r = i * 2
        for d in range(1, NDAYS + 1):
            e = self.entry(i, d)
            c = COL_FIRST + d - 1
            merged = e.get("m") in MERGED
            self.setSpan(r, c, 2 if merged else 1, 1)
            for half, rr in (("m", r), ("p", r + 1)):
                it = self.item(rr, c)
                txt = e.get(half, "")
                if merged:
                    shown = "-" if e.get("cont") else txt
                    it.setText(shown + ("#" if e.get("g") else "") if half == "m" else "")
                else:
                    gett = half in e.get("g", ()) and txt != ""
                    it.setText(txt + ("#" if gett else ""))
                it.setForeground(QBrush(TEXT_COLORS.get(txt, QColor("black"))))
                it.setBackground(QBrush(WEEKEND if self.weekend(d) else QColor("white")))
        total, ngett = self.calc_row(i)
        t = self.item(r, COL_TOT)
        t.setText(f"{fmt(total)} / {fmt(TARGET)}" + (f"\n{ngett} gettoni" if ngett else ""))
        t.setForeground(QBrush(QColor("#0a7d00" if total >= TARGET else "#000")))
        self.update_counters()
        if self.ready:
            self.save()

    def update_counters(self):
        self.style_headers()
        f = self.footer
        if f is None:
            return
        ERR, OK = QColor("#ff9a9a"), QColor("#eeeeee")
        f.blockSignals(True)
        for k, code in enumerate(("SO", "SOP")):
            tot_a = tot_p = 0
            for d in range(1, NDAYS + 1):
                c = COL_FIRST + d - 1
                a = sum(1 for (j, dd), e in self.data.items()
                        if dd == d and code in (e.get("m"), e.get("p")))
                p = self.programmed(k, d)
                tot_a += a
                tot_p += p
                f.item(k, c).setText(str(a) if a else "")
                bad = QBrush(ERR if a != p else OK)
                f.item(k, c).setBackground(bad)
                f.item(k + 2, c).setBackground(QBrush(ERR if a != p else QColor("white")))
            f.item(k, COL_TOT).setText(str(tot_a))
            f.item(k + 2, COL_TOT).setText(str(tot_p))
            bad = QBrush(ERR if tot_a != tot_p else OK)
            f.item(k, COL_TOT).setBackground(bad)
            f.item(k + 2, COL_TOT).setBackground(bad)
        f.blockSignals(False)

    def programmed(self, k, d):
        it = self.footer.item(k + 2, COL_FIRST + d - 1)
        try:
            return int(it.text())
        except ValueError:
            return 0
    def on_enter(self, row, col):
        self.hover = (row, col)
        if not self.drag_start:
            self.timer.start()

    def leaveEvent(self, ev):
        self.timer.stop()
        super().leaveEvent(ev)

    def cell_info(self, row, col):
        if not (COL_FIRST <= col < COL_TOT) or not DOCTORS[row // 2]:
            return None
        return row // 2, col - COL_FIRST + 1, ("m" if row % 2 == 0 else "p")

    def taken_by(self, code, d, i):
        if code not in UNIQUE:
            return None
        for (j, dd), e in self.data.items():
            if dd == d and j != i and code in (e.get("m"), e.get("p")):
                return DOCTORS[j]
        return None

    def open_menu(self):
        if not self.hover:
            return
        info = self.cell_info(*self.hover)
        if not info:
            return
        i, d, half = info
        opts = self.options(i, d, half)
        if not opts:
            return
        row, col = self.hover
        menu = QMenu(self)
        for o in opts:
            who = self.taken_by(o, d, i)
            pm_ctx = half == "p" or "m" in self.entry(i, d)
            hrs = 6 * 60 if pm_ctx and o == "TA" else HOURS.get(o)
            label = f"{o}  ({fmt(hrs)}h)" if hrs is not None else "-  (continua)"
            a = menu.addAction(label + (f"  - {who}" if who else ""))
            a.setData(o)
            a.setEnabled(not who)
        menu.addSeparator()
        menu.addAction("Altro (sigla libera)...").setData(CUSTOM)
        pos = QPoint(self.columnViewportPosition(col),
                     self.rowViewportPosition(row) + self.rowHeight(row))
        act = menu.exec(self.viewport().mapToGlobal(pos))
        if act:
            code = act.data()
            if code == CUSTOM:
                code, ok = QInputDialog.getText(self, "Sigla libera", "Sigla:")
                code = code.strip()
                if not ok or not code:
                    return
            self.assign(i, d, half, code)

    def snapshot(self, with_prog=False):
        prog = None
        if with_prog and self.footer:
            prog = {(k, d): self.footer.item(k, COL_FIRST + d - 1).text()
                    for k in (2, 3) for d in range(1, NDAYS + 1)}
        return copy.deepcopy(self.data), dict(self.notes), prog, dict(CUSTOM_HOL)

    def push_undo(self, with_prog=False):
        self.undo_stack.append(self.snapshot(with_prog))
        del self.undo_stack[:-100]

    def undo(self):
        if not self.undo_stack:
            return False
        data, notes, prog, hol = self.undo_stack.pop()
        self.ready = False
        self.data, self.notes = data, notes
        CUSTOM_HOL.clear()
        CUSTOM_HOL.update(hol)
        self.style_headers()
        self.refresh_notes()
        if prog is not None:
            self.footer.blockSignals(True)
            for (k, d), v in prog.items():
                self.footer.item(k, COL_FIRST + d - 1).setText(v)
            self.footer.blockSignals(False)
        for i, name in enumerate(DOCTORS):
            if name:
                self.refresh_row(i)
        self.update_counters()
        self.ready = True
        self.save()
        return True

    def assign(self, i, d, half, code):
        self.push_undo()
        if code == "-":
            prev = self.entry(i, d - 1).get("m")
            self.data[(i, d)] = {"m": prev, "p": prev, "cont": True}
            self.refresh_row(i)
            return
        if code in AFTERNOON or (code == "TA" and half == "m" and "m" in self.entry(i, d)):
            half = "p"
        if code in FULL or code in BLOCK:
            self.data[(i, d)] = {"m": code, "p": code}
        else:
            self.data.setdefault((i, d), {})[half] = code
        self.refresh_row(i)

    def merged_menu(self, i, d, e, pos):
        g = e.setdefault("g", set())
        menu = QMenu(self)
        a_add = a_rem = None
        if e["m"] not in BLOCK:
            a_add = menu.addAction(f"Aggiungi gettone # (-{fmt(HOURS[e['m']])}h)")
            a_add.setEnabled(not g)
            a_rem = menu.addAction("Rimuovi gettone")
            a_rem.setEnabled(bool(g))
        a_del = menu.addAction("Elimina turno")
        act = menu.exec(pos)
        if act is None:
            return
        self.push_undo()
        if act is a_add:
            g.add("m" if "m" not in g else "p")
        elif act is a_rem:
            g.discard("p" if "p" in g else "m")
        elif act is a_del:
            first = not e.get("cont")
            self.data.pop((i, d), None)
            n = d + 1
            while first and self.entry(i, n).get("cont"):
                self.data.pop((i, n), None)
                n += 1
        self.refresh_row(i)

    def fill_continue(self, i, d1, d2):
        self.push_undo()
        code = self.entry(i, d1).get("m")
        for d in range(d1 + 1, d2 + 1):
            if self.entry(i, d) or self.after_night(i, d):
                break
            self.data[(i, d)] = {"m": code, "p": code, "cont": True}
        self.refresh_row(i)

    def mouseReleaseEvent(self, ev):
        start, self.drag_start = self.drag_start, None
        if start and ev.button() == Qt.LeftButton:
            idx = self.indexAt(ev.position().toPoint())
            info = self.cell_info(idx.row(), idx.column())
            if info and info[0] == start[0] and info[1] > start[1]:
                self.fill_continue(start[0], start[1], info[1])
        super().mouseReleaseEvent(ev)

    def save(self, path=None):
        out = {}
        for (j, d), e in self.data.items():
            out.setdefault(DOCTORS[j], {})[str(d)] = {
                **{k: v for k, v in e.items() if k != "g"}, "g": sorted(e.get("g", ()))}
        out["__programmate__"] = {code: {str(d): self.programmed(k, d) for d in range(1, NDAYS + 1)
                                         if self.programmed(k, d)}
                                  for k, code in enumerate(("SO", "SOP"))} if self.footer else {}
        out["__note__"] = {str(d): t for d, t in self.notes.items()}
        out["__festivi__"] = {str(d): t for d, t in CUSTOM_HOL.items()}
        if path is None:
            backup(save_file())
        with open(path or save_file(), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)

    def load(self, path=None):
        path = path or save_file()
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.ready = False
        self.data = {}
        prog = raw.pop("__programmate__", {})
        self.notes = {int(d): t for d, t in raw.pop("__note__", {}).items() if int(d) <= NDAYS}
        CUSTOM_HOL.clear()
        CUSTOM_HOL.update({int(d): t for d, t in raw.pop("__festivi__", {}).items() if int(d) <= NDAYS})
        self.style_headers()
        self.refresh_notes()
        if self.footer:
            self.footer.blockSignals(True)
            for k, code in enumerate(("SO", "SOP")):
                for d in range(1, NDAYS + 1):
                    v = prog.get(code, {}).get(str(d), "")
                    self.footer.item(k + 2, COL_FIRST + d - 1).setText(str(v))
            self.footer.blockSignals(False)
        for name, days in raw.items():
            if name not in DOCTORS:
                continue
            i = DOCTORS.index(name)
            for d, e in days.items():
                self.data[(i, int(d))] = {
                    **{k: ("AGP" if v == "AG pom" else v) for k, v in e.items() if k != "g"}, "g": set(e.get("g", []))}
        for i, name in enumerate(DOCTORS):
            if name:
                self.refresh_row(i)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            idx = self.indexAt(ev.position().toPoint())
            info = self.cell_info(idx.row(), idx.column())
            if info:
                i, d, half = info
                e = self.entry(i, d)
                if half not in e:
                    return
                if e.get("m") in MERGED:
                    self.merged_menu(i, d, e, ev.globalPosition().toPoint())
                    return
                menu = QMenu(self)
                g = half in e.get("g", set())
                a_g = menu.addAction("Rimuovi gettone" if g else f"Converti in gettone # (-{fmt(GETTONE_H)}h)")
                a_g.setEnabled(e[half] not in BLOCK)
                a_d = menu.addAction("Elimina turno")
                act = menu.exec(ev.globalPosition().toPoint())
                if act:
                    self.push_undo()
                if act is a_g:
                    e.setdefault("g", set()).symmetric_difference_update({half})
                elif act is a_d:
                    if e.get("m") == e.get("p") and e.get("m") in (*FULL, *BLOCK):
                        self.data.pop((i, d), None)
                    else:
                        e.pop(half, None)
                        e.get("g", set()).discard(half)
                        if not (e.get("m") or e.get("p")):
                            self.data.pop((i, d), None)
                self.refresh_row(i)
            return
        if ev.button() == Qt.LeftButton:
            self.timer.stop()
            idx = self.indexAt(ev.position().toPoint())
            if self.sep_row is not None and idx.row() // 2 == self.sep_row // 2 and COL_FIRST <= idx.column() < COL_TOT:
                self.note_menu(idx.column() - COL_FIRST + 1, ev.globalPosition().toPoint())
                return
            info = self.cell_info(idx.row(), idx.column())
            if info and self.entry(info[0], info[1]).get("m") in CONTINUABLE:
                self.drag_start = (info[0], info[1])
        super().mousePressEvent(ev)


SPECIALITA = ["ORL", "GIN", "CHIR GEN", "URO", "CHIR VASC", "ORT sala B", "ORT sala A"]
WEEK_SCHEMA = {
    0: {"SO": ["ORL", "CHIR GEN", "URO", "ORT sala A"], "SOP": ["URO", "ORT sala A"]},
    1: {"SO": ["ORL", "GIN", "CHIR VASC", "ORT sala A"], "SOP": ["URO", "ORT sala A"]},
    2: {"SO": ["CHIR GEN", "URO", "ORT sala B", "ORT sala A"], "SOP": ["URO", "ORL"]},
    3: {"SO": ["ORL", "CHIR GEN", "URO", "ORT sala A"], "SOP": ["URO"]},
    4: {"SO": ["ORL", "CHIR GEN", "URO", "ORT sala A"], "SOP": []},
}
LC = 3  # colonne etichetta del compilatore settimanale
PDF_NAMES = {"ORL": "O.R.L.", "GIN": "GINECOLOGIA", "CHIR GEN": "CHIRURGIA", "URO": "UROLOGIA",
             "CHIR VASC": "CHIR./VASC.", "ORT sala A": "ORTOPEDIA A", "ORT sala B": "ORTOPEDIA B"}
WEEK_GUARDIE = ["RM", "U", "RG", "RN", "AG", "AGP", "AN"]
WEEK_ROWS = [("RIA_M", ("RM", "RG")), ("RIA_P", ("RG",)), ("RN", ("RN",)), ("U", ("U",)), ("AG", ("AG",)),
             ("AGP", ("AGP",)), ("AN", ("AN",)), ("P", ("P",)), ("TA", ("TA",)), ("TAP", ("TAP",))]
WEEK_REQUIRED = ("RM", "RG", "RN", "U", "AG", "AGP", "AN")
WEEK_LABELS = {
    "RIA_M": "Rianimazione giorno 8-14", "RIA_P": "Rianimazione giorno 14-20", "U": "Urgenze 8-14",
    "RN": "Gu. Rianim. notte 20-8", "AG": "Anestesia giorno 8-20", "AGP": "Anestesia pomeriggio 14-20",
    "AN": "Gu. Anest. notte 20-8", "P": "Ambulatorio pomeriggio 14-20", "TA": "Terapia antalgica 8-14",
    "TAP": "Terapia antalgica 14-20"}


def week_has(c, m, p):
    if c == "TA":
        return m == "TA"
    if c == "TAP":
        return p == "TA"
    return c in (m, p)
GIORNI_LUNGHI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


def weekly_file():
    return os.path.join(base_dir(), "turni_settimane.json")


class WeeklyDialog(QDialog):
    def __init__(self, parent, start):
        super().__init__(parent)
        self.setWindowTitle("Turno settimanale")
        self.months = {}
        self.store = {}
        if os.path.exists(weekly_file()):
            try:
                with open(weekly_file(), encoding="utf-8") as f:
                    self.store = json.load(f)
            except (OSError, ValueError):
                self.store = {}
        self.monday = start - datetime.timedelta(days=start.weekday())
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        b_prev = QPushButton("\u25c0")
        b_next = QPushButton("\u25b6")
        self.lbl = QLabel()
        self.lbl.setStyleSheet("font-weight:bold;font-size:14px")
        b_prev.clicked.connect(lambda: self.shift(-7))
        b_next.clicked.connect(lambda: self.shift(7))
        for w in (b_prev, self.lbl, b_next):
            top.addWidget(w)
        top.addStretch()
        top.addWidget(QLabel("Clic sul giorno in alto: scegli le specialità"))
        b_reset = QPushButton("Azzera assegnazioni")
        b_reset.clicked.connect(self.reset_assign)
        top.addWidget(b_reset)
        b_pdf = QPushButton("Esporta PDF")
        b_pdf.clicked.connect(self.save_pdf)
        top.addWidget(b_pdf)
        lay.addLayout(top)
        self.tab = QTableWidget()
        self.tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tab.setSelectionMode(QAbstractItemView.NoSelection)
        self.tab.cellClicked.connect(self.cell_clicked)
        self.tab.horizontalHeader().sectionClicked.connect(self.edit_day_specs)
        self.tab.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab.customContextMenuRequested.connect(self.cell_menu)
        lay.addWidget(self.tab)
        hint = QLabel("Clic su un nome nelle righe SO / SOP per assegnarlo a una specialità o scambiarlo con un'altra.")
        hint.setStyleSheet("color:#555")
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(1250, 760)
        self.setWindowState(Qt.WindowMaximized)
        self.fill()

    def month_data(self, y, m):
        if (y, m) not in self.months:
            p = os.path.join(base_dir(), f"turni_{y}_{m:02d}.json")
            data = {}
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                except (OSError, ValueError):
                    data = {}
            self.months[(y, m)] = data
        return self.months[(y, m)]

    def entries(self, day):
        raw = self.month_data(day.year, day.month)
        out = []
        for name, days in raw.items():
            if name.startswith("__"):
                continue
            e = days.get(str(day.day))
            if e:
                m, p = e.get("m"), e.get("p")
                p = "AGP" if p == "AG pom" else p
                out.append((name, m, p))
        return out

    def is_off(self, d):
        if d.weekday() >= 5 or (d.month, d.day) in holidays(d.year):
            return True
        return str(d.day) in self.month_data(d.year, d.month).get("__festivi__", {})

    def expected(self, code, d):
        off = self.is_off(d)
        if code in ("RM", "U", "AGP"):
            return not off
        if code == "AG":
            return off
        return True

    def export_pdf(self, path):
        w = QPdfWriter(path)
        w.setPageSize(QPageSize(QPageSize.A4))
        w.setPageOrientation(QPageLayout.Landscape)
        w.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter)
        w.setResolution(150)
        self.render_sheet(w)

    def render_sheet(self, dev):
        p = QPainter(dev)
        W, H = p.device().width(), p.device().height()
        cyan, grey, yellow = QColor("#ccffff"), QColor("#c0c0c0"), QColor("#ffff99")
        orange, green, red = QColor("#ffcc00"), QColor("#66ff33"), QColor("#ff0000")
        S = W / 1280.0
        wn, wm, wt = 60 * S, 165 * S, 85 * S
        x0 = wn + wm + wt
        cw = (W - x0) / 7
        G = {r[1]: r[2] for r in self.rows if r[0] == "g"}
        spec_rows = [r for r in self.rows if r[0] in ("SO", "SOP") and r[1] is not None]
        todo = [r for r in self.rows if r[0] in ("SO", "SOP") and r[1] is None and any(r[2])]
        off = [self.is_off(d) for d in self.days]

        def txt(c, k):
            return "\n".join(c[k])

        # (weight) layout of rows
        top = [("hdr", 1.7), ("ria_m", 1.5), ("ria_p", 1.0), ("rn", 1.0), ("u", 1.4), ("agp", 1.4), ("an", 1.0)]
        spec = [(i, 1.1) for i in range(len(spec_rows))]
        bottom = [("p", 1.5), ("ta", 1.5)] + ([("tap", 1.5)] if any(G["TAP"][k] for k in range(7)) else [])
        gap = 0.35
        total = sum(h for _, h in top) + sum(h for _, h in spec) + gap * 2 + sum(h for _, h in bottom) + 1.0 \
            + sum(max(0.9, 0.5 * max(len(c) for c in r[2])) for r in todo)
        unit = (H - 30 * S) / total
        blk_h = {}

        def box(x, y, wd, h, text, bg=None, bold=True, pt=12.0, fg=Qt.black, align=Qt.AlignCenter):
            r = QRectF(x, y, wd, h)
            if bg:
                p.fillRect(r, bg)
            if not text:
                return
            f = QFont("Times New Roman", 1, QFont.Bold if bold else QFont.Normal)
            f.setPointSizeF(pt)
            flags = int(align) | int(Qt.TextWordWrap)
            inner = r.adjusted(3, 1, -3, -1)
            while f.pointSizeF() > 4:
                fm = QFontMetricsF(f, p.device())
                longest = max(fm.horizontalAdvance(s) for s in text.replace("\n", " ").split(" "))
                if longest <= inner.width() and fm.boundingRect(inner, flags, text).height() <= inner.height() + 1:
                    break
                f.setPointSizeF(f.pointSizeF() - 0.5)
            p.setFont(f)
            p.setPen(fg)
            p.drawText(inner, flags, text)

        def line(x1, y1, x2, y2, wd=1.0, dotted=False):
            pen = QPen(Qt.black, wd * S * 1.4)
            if dotted:
                pen.setStyle(Qt.DotLine)
                pen.setWidthF(S)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        def vlines(ya, yb):
            for k in range(8):
                line(x0 + k * cw, ya, x0 + k * cw, yb)
            line(wn + wm, ya, wn + wm, yb)

        y = 0.0
        # header
        hh = 1.7 * unit
        box(0, y, wn + wm + wt, hh, f"{MESI[self.days[0].month - 1].upper()} {self.days[0].year}", cyan, True, 20, red)
        for k, d in enumerate(self.days):
            fg = red if off[k] else Qt.black
            bg = yellow if off[k] else cyan
            box(x0 + k * cw, y, cw, hh / 2, GIORNI_LUNGHI[k], bg, off[k], 15, fg)
            box(x0 + k * cw, y + hh / 2, cw, hh / 2, str(d.day), bg, True, 15, fg)
        ytop = y
        y += hh
        # top sections
        rg = [list(G["RIA_P"][k]) for k in range(7)]
        rm = []
        for k in range(7):
            l = list(G["RIA_M"][k])
            for n in G["RIA_P"][k]:
                if n in l:
                    l.remove(n)
            rm.append(l)
        sec = [
            ("RIANIMAZIONE\nGIORNO", "8-14", "ria_m", 1.5, None, None),
            ("", "14-20", "ria_p", 1.0, None, None),
            ("GU. RIANIM. NOTTE", "20-8", "rn", 1.0, grey, None),
            ("URGENZE", "8-14", "u", 1.4, yellow, red),
            ("ANESTESIA\nPOMERIGGIO", "14-20", "agp", 1.4, None, None),
            ("GU. ANEST. NOTTE", "20-8", "an", 1.0, grey, None),
        ]
        ys = {}
        for lab, tm, key, wgt, bg, fg in sec:
            h = wgt * unit
            ys[key] = (y, h)
            if lab:
                span = 2 if key == "ria_m" else 1
                hl = h + (1.0 * unit if key == "ria_m" else 0)
                two = key in ("rn", "an", "u")
                box(0, y, wn + wm if not two else wn + wm, hl, lab, bg, True, 14, fg or Qt.black)
            box(wn + wm, y, wt, h, tm, bg, False, 14)
            for k in range(7):
                if key == "ria_m" and ("RIA_M", k) in self.ovr:
                    t = txt(G["RIA_M"], k)
                elif key == "ria_m":
                    t = " – ".join(rg[k] + rm[k])
                elif key == "ria_p":
                    t = " – ".join(rg[k])
                elif key == "rn":
                    t = txt(G["RN"], k)
                elif key == "an":
                    t = txt(G["AN"], k)
                elif key == "u":
                    t = txt(G["U"], k)
                else:
                    t = txt(G["AGP"], k)
                cbg = yellow if (off[k] and key in ("u", "agp", "ria_m", "ria_p")) else (grey if key in ("rn", "an") else (yellow if key == "u" else None))
                box(x0 + k * cw, y, cw, h, t.upper(), cbg, True, 12)
            y += h
        yend = y
        vlines(ytop + hh, yend)
        for k in range(8):
            line(x0 + k * cw, ytop, x0 + k * cw, ytop + hh)
        for key in ("ria_m", "rn", "u", "agp", "an"):
            ya = ys[key][0]
            line(0, ya, W, ya, 2.2)
        line(0, ytop, W, ytop, 2.2)
        line(0, yend, W, yend, 2.2)
        line(wn + wm, ys["ria_p"][0], W, ys["ria_p"][0], 1, True)
        line(0, ytop, 0, yend, 2.2)
        line(W, ytop, W, yend, 2.2)
        # specialties
        y = yend + gap * unit
        ysp = y
        for i in range(0, len(spec_rows), 2):
            pair = spec_rows[i:i + 2]
            yb = y
            for r, (kind, label, cells) in enumerate(pair):
                h = 1.1 * unit
                box(wn + wm, y, wt, h, "8-14.30" if kind == "SO" else "14-20", None, False, 14)
                for k in range(7):
                    t = txt(cells, k)
                    if off[k] and not t:
                        continue
                    box(x0 + k * cw, y, cw, h, (t or "X").upper(), orange if t else None, bool(t), 12)
                y += h
            n = i // 2 + 1
            box(0, yb, wn, y - yb, str(n), None, True, 14)
            box(wn, yb, wm, y - yb, PDF_NAMES.get(pair[0][1], pair[0][1].upper()), None, True, 14)
            line(wn + wm, yb + (y - yb) / 2, W, yb + (y - yb) / 2, 1, True)
            line(0, y, W, y, 2.2)
        yspec_end = y
        for t_r in todo:
            h = max(0.9, 0.5 * max(len(c) for c in t_r[2])) * unit
            box(0, y, wn + wm + wt, h, "DA ASSEGNARE " + ("MATTINA" if t_r[0] == "SO" else "POMERIGGIO"), None, True, 11, red)
            for k in range(7):
                box(x0 + k * cw, y, cw, h, txt(t_r[2], k).upper(), None, True, 11, red)
            y += h
            line(0, y, W, y, 1)
        line(0, ysp, W, ysp, 2.2)
        vlines(ysp, yspec_end)
        line(wn, ysp, wn, yspec_end)
        for k in range(8):
            line(x0 + k * cw, yspec_end, x0 + k * cw, y)
        line(0, ysp, 0, y, 2.2)
        line(W, ysp, W, y, 2.2)
        # ambulatori
        y += gap * unit
        yb0 = y
        has_tap = any(G["TAP"][k] for k in range(7))
        for key, lab, tm, bg in (("P", "AMBULATORIO\nPOMERIGGIO", "14-20", orange), ("TA", "TERAPIA ANTALGICA", "8-14", green),
                                 *((("TAP", "TERAPIA ANTALGICA\nPOMERIGGIO", "14-20", green),) if has_tap else ())):
            h = 1.5 * unit
            box(0, y, wn + wm, h, lab, bg if key != "P" else None, True, 13)
            box(wn + wm, y, wt, h, tm, None, False, 14)
            for k in range(7):
                t = txt(G[key], k)
                if off[k] and not t:
                    continue
                box(x0 + k * cw, y, cw, h, (t or "---").upper(), bg, True, 12)
            y += h
            line(0, y, W, y, 2.2 if key == ("TAP" if has_tap else "TA") else 1)
        line(0, yb0, W, yb0, 2.2)
        vlines(yb0, y)
        line(0, yb0, 0, y, 2.2)
        line(W, yb0, W, y, 2.2)
        p.setPen(Qt.black)
        p.setFont(QFont("Times New Roman", 11))
        p.drawText(QRectF(0, y + 8 * S, W, 30 * S), Qt.AlignLeft | Qt.AlignVCenter, "Data ____________________")
        p.setFont(QFont("Times New Roman", 9, QFont.Normal, True))
        p.drawText(QRectF(0, H - 24 * S, W, 24 * S), Qt.AlignRight | Qt.AlignBottom, "Made with Moreno \u00a9")
        p.end()

    def reset_assign(self):
        box = QMessageBox(self)
        box.setWindowTitle("Azzera assegnazioni")
        box.setText("Azzerare le assegnazioni alle sale di questa settimana?")
        b_auto = box.addButton("Ripristina automatico", QMessageBox.AcceptRole)
        b_empty = box.addButton("Svuota tutto", QMessageBox.DestructiveRole)
        box.addButton("Annulla", QMessageBox.RejectRole)
        box.exec()
        w = self.week()
        if box.clickedButton() is b_auto:
            w.pop("assign", None)
        elif box.clickedButton() is b_empty:
            w["assign"] = {f"{kind}|{d.isoformat()}|{n}": "-"
                           for kind in ("SO", "SOP") for k, d in enumerate(self.days) for n in self.pool[kind][k]}
        else:
            return
        self.persist()
        self.fill()

    def save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Esporta PDF", f"turno_settimanale_{self.monday:%Y_%m_%d}.pdf", "PDF (*.pdf)")
        if path:
            self.export_pdf(path)
            os.startfile(path)

    def week(self):
        return self.store.setdefault(self.monday.isoformat(), {})

    def specs(self):
        days = [self.monday + datetime.timedelta(days=k) for k in range(7)]
        act = {s for d in days for kind in ("SO", "SOP") for s in self.day_specs(kind, d)}
        return [s for s in SPECIALITA if s in act]

    def day_specs(self, kind, day):
        w = self.week()
        v = w.get("dayspecs", {}).get(f"{kind}|{day.isoformat()}")
        if v is None:
            v = WEEK_SCHEMA.get(day.weekday(), {}).get(kind, [])
            if "specs" in w:
                v = [s for s in v if s in w["specs"]]
        return [s for s in SPECIALITA if s in v]

    def spec_of(self, kind, day, name):
        s = self.week().get("assign", {}).get(f"{kind}|{day.isoformat()}|{name}")
        if s is None:
            return self.auto.get((kind, day.isoformat(), name))
        return s if s in self.day_specs(kind, day) else None

    def build_auto(self, days):
        self.auto = {}
        assign = self.week().get("assign", {})
        for kind in ("SO", "SOP"):
            for k, d in enumerate(days):
                names = self.pool[kind][k]
                keys = {n: f"{kind}|{d.isoformat()}|{n}" for n in names}
                occupied = {assign[keys[n]] for n in names if keys[n] in assign}
                free = [s for s in self.day_specs(kind, d) if s not in occupied]
                autos = [n for n in names if keys[n] not in assign]
                for n, s in zip(autos, free):
                    self.auto[(kind, d.isoformat(), n)] = s

    def set_spec(self, kind, day, name, spec):
        a = self.week().setdefault("assign", {})
        a[f"{kind}|{day.isoformat()}|{name}"] = spec or "-"
        self.persist()

    def persist(self):
        with open(weekly_file(), "w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False, indent=1)

    def shift(self, n):
        self.monday += datetime.timedelta(days=n)
        self.fill()

    def edit_day_specs(self, col):
        k = col - LC
        if not 0 <= k < 7:
            return
        day = self.days[k]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Specialità di {GIORNI_LUNGHI[k]} {day:%d/%m}")
        lay = QVBoxLayout(dlg)
        cols = QHBoxLayout()
        lists = {}
        for kind, title in (("SO", "Mattina (SO)"), ("SOP", "Pomeriggio (SOP)")):
            box = QVBoxLayout()
            box.addWidget(QLabel(f"<b>{title}</b>"))
            lst = QListWidget()
            cur = self.day_specs(kind, day)
            for s in SPECIALITA:
                it = QListWidgetItem(s)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if s in cur else Qt.Unchecked)
                lst.addItem(it)
            box.addWidget(lst)
            cols.addLayout(box)
            lists[kind] = lst
        lay.addLayout(cols)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        reset = []
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(lambda: (reset.append(1), dlg.accept()))
        lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        ds = self.week().setdefault("dayspecs", {})
        for kind, lst in lists.items():
            key = f"{kind}|{day.isoformat()}"
            if reset:
                ds.pop(key, None)
            else:
                ds[key] = [s for i, s in enumerate(SPECIALITA) if lst.item(i).checkState() == Qt.Checked]
        self.persist()
        self.fill()

    def fill(self):
        mon = self.monday
        days = [mon + datetime.timedelta(days=k) for k in range(7)]
        self.days = days
        self.lbl.setText(f"  Settimana dal {days[0]:%d/%m/%Y} al {days[6]:%d/%m/%Y}  ")
        specs = self.specs()
        ents = [self.entries(d) for d in days]
        rows = []
        for key, codes in WEEK_ROWS:
            cells = []
            for k, e in enumerate(ents):
                names = [n for n, m, p in e if any(week_has(c, m, p) for c in codes)]
                for c in codes:
                    if c in WEEK_REQUIRED and self.expected(c, days[k]) and not any(week_has(c, m, p) for n, m, p in e):
                        names.append("/" if f"{c}|{days[k].isoformat()}" in self.week().get("missing", []) else "?")
                cells.append(names)
            rows.append(("g", key, cells))
        ag = next(c for kd, lb, c in rows if lb == "AG")
        for i, (kd, lb, cells) in enumerate(rows):
            if lb in ("U", "AGP"):
                rows[i] = (kd, lb, [ag[k] if self.expected("AG", days[k]) else cells[k] for k in range(7)])
        self.ag_hidden = True
        self.pool = {}
        for kind in ("SO", "SOP"):
            self.pool[kind] = [[n for n, m, p in e if (m == "SO" if kind == "SO" else p == "SOP")] for e in ents]
        self.build_auto(days)
        for s in specs:
            for kind in ("SO", "SOP"):
                pool = self.pool[kind]
                rows.append((kind, s, [[n for n in pool[k] if self.spec_of(kind, days[k], n) == s] for k in range(7)]))
        for kind in ("SO", "SOP"):
            pool = self.pool[kind]
            rows.append((kind, None, [[n for n in pool[k] if self.spec_of(kind, days[k], n) is None] for k in range(7)]))
        ov = self.week().get("override", {})
        self.ovr = set()
        for i, (kd, lb, cells) in enumerate(rows):
            rk = lb if kd == "g" else f"{kd}:{lb or ''}"
            new = []
            for k in range(7):
                v = ov.get(f"{rk}|{days[k].isoformat()}")
                if v is None:
                    new.append(cells[k])
                else:
                    self.ovr.add((rk, k))
                    new.append([x.strip() for x in v.split("\n") if x.strip()])
            rows[i] = (kd, lb, new)
        self.rows = rows
        t = self.tab
        t.clear()
        t.setRowCount(len(rows))
        t.setColumnCount(LC + 7)
        t.setHorizontalHeaderLabels(["", "", ""] + [f"{GIORNI_LUNGHI[k]} {d:%d/%m} \u25be" for k, d in enumerate(days)])
        for k, d in enumerate(days):
            if is_weekend_date(d):
                hi = t.horizontalHeaderItem(LC + k)
                hi.setBackground(QBrush(QColor("#ffff99")))
                hi.setForeground(QBrush(QColor("#d00000")))
        t.verticalHeader().hide()
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        t.setColumnWidth(0, 34)
        t.setColumnWidth(2, 130)
        t.verticalHeader().setDefaultSectionSize(30)
        bold = QFont()
        bold.setBold(True)
        gfont = QFont()
        gfont.setBold(True)
        gfont.setPointSize(11)

        def lab(r, c, text, bg=None, fg=None, rs=1, cs=1):
            li = QTableWidgetItem(text)
            li.setFont(bold)
            li.setTextAlignment(Qt.AlignCenter)
            li.setBackground(QBrush(QColor(bg or "#f2f2f2")))
            if fg:
                li.setForeground(QBrush(QColor(fg)))
            t.setItem(r, c, li)
            if rs > 1 or cs > 1:
                t.setSpan(r, c, rs, cs)

        t.clearSpans()
        spec_n = 0
        for r, (kind, label, cells) in enumerate(rows):
            if kind == "g" and label == "AG":
                continue
            if kind == "g":
                lab(r, 0, WEEK_LABELS.get(label, label), {"RN": "#c8c8c8", "AN": "#c8c8c8", "U": "#ffff99"}.get(label, "#ffffff"), cs=3)
            elif label is None:
                lab(r, 0, "DA ASSEGNARE " + ("MATTINA" if kind == "SO" else "POMERIGGIO"), "#ffe0e0", "#c00000", cs=3)
            else:
                if kind == "SO":
                    spec_n += 1
                    lab(r, 0, f"{spec_n}", "#dcdcdc", rs=2)
                    lab(r, 1, PDF_NAMES.get(label, label), "#dcdcdc", rs=2)
                lab(r, 2, "MATTINA 8-14.30" if kind == "SO" else "POMERIGGIO 14-20",
                    "#cfe8ff" if kind == "SO" else "#ffe3b8")
        for r, (kind, label, cells) in enumerate(rows):
            for c in range(7):
                txt = "\n".join(cells[c])
                if not txt and kind in ("SO", "SOP") and label is not None:
                    txt = "X"
                it = QTableWidgetItem(txt)
                if kind == "g":
                    code = {"RIA_M": "RM", "RIA_P": "RG", "TAP": "TA"}.get(label, label)
                    it.setForeground(QBrush(TEXT_COLORS.get(code, QColor("black"))))
                    it.setFont(gfont)
                    if label in ("RN", "AN"):
                        it.setBackground(QBrush(QColor("#c8c8c8")))
                    elif label == "U" or is_weekend_date(days[c]):
                        it.setBackground(QBrush(QColor("#ffff99")))
                    if "?" in cells[c]:
                        it.setForeground(QBrush(QColor("#c00000")))
                        it.setBackground(QBrush(QColor("#ffd0d0")))
                elif label is None:
                    it.setForeground(QBrush(QColor("#c00000")))
                elif txt != "X":
                    it.setBackground(QBrush(QColor("#ffcc00")))
                elif is_weekend_date(days[c]):
                    it.setBackground(QBrush(QColor("#ffffa8")))
                it.setTextAlignment(Qt.AlignCenter)
                if (self.row_key(r), c) in self.ovr:
                    f = it.font()
                    f.setUnderline(True)
                    it.setFont(f)
                    it.setToolTip("Modificato a mano (tasto destro per ripristinare)")
                t.setItem(r, LC + c, it)
            t.setRowHeight(r, max(26, 18 * max(len(x) for x in cells) + 8))
            t.setRowHidden(r, kind == "g" and label == "AG" and self.ag_hidden)

    def row_key(self, r):
        kind, label, _cells = self.rows[r]
        return label if kind == "g" else f"{kind}:{label or ''}"

    def cell_menu(self, pos):
        r, c = self.tab.rowAt(pos.y()), self.tab.columnAt(pos.x()) - LC
        if r < 0 or c < 0:
            return
        rk, day = self.row_key(r), self.days[c]
        key = f"{rk}|{day.isoformat()}"
        menu = QMenu(self)
        menu.addAction("Modifica a mano...", lambda: self.force_edit(r, c, key))
        if (rk, c) in self.ovr:
            menu.addAction("Ripristina valore automatico", lambda: self.force_clear(key))
        menu.exec(QCursor.pos())

    def force_edit(self, r, c, key):
        cur = "\n".join(x for x in self.rows[r][2][c] if x not in ("?", "/"))
        text, ok = QInputDialog.getMultiLineText(
            self, "Modifica a mano", f"{self.days[c]:%d/%m} - un nome per riga.\nSvuota il testo per tornare al valore automatico. Scrivi - per lasciare vuoto.", cur)
        if not ok:
            return
        ov = self.week().setdefault("override", {})
        if text.strip():
            ov[key] = text.strip()
        else:
            ov.pop(key, None)
        self.persist()
        self.fill()

    def force_clear(self, key):
        self.week().get("override", {}).pop(key, None)
        self.persist()
        self.fill()

    def cell_clicked(self, r, c):
        c -= LC
        if c < 0:
            return
        if (self.row_key(r), c) in self.ovr:
            return
        kind, label, cells = self.rows[r]
        day = self.days[c]
        if kind == "g":
            if label in ("U", "AGP") and self.expected("AG", day):
                label = "AG"
            codes = dict(WEEK_ROWS)[label]
            ents = self.entries(day)
            miss = [x for x in codes if x in WEEK_REQUIRED and self.expected(x, day)
                    and not any(week_has(x, m, p) for n, m, p in ents)]
            lst = self.week().setdefault("missing", [])
            for x in miss:
                key = f"{x}|{day.isoformat()}"
                if key in lst:
                    if QMessageBox.question(self, "Turno settimanale", f"Annullare la conferma di {x} mancante il {day:%d/%m}?") == QMessageBox.Yes:
                        lst.remove(key)
                else:
                    if QMessageBox.question(self, "Turno settimanale",
                                            f"Nel mensile manca {x} il {day:%d/%m}.\nHai verificato che siamo una persona in meno? Segno \"/\".") == QMessageBox.Yes:
                        lst.append(key)
            if miss:
                self.persist()
                self.fill()
            return
        if kind not in ("SO", "SOP"):
            return
        menu = QMenu(self)
        specs = self.day_specs(kind, day)
        if not cells[c] and label is not None:
            for n in self.rows_for(kind, None)[c]:
                menu.addAction(f"Assegna {n}", lambda n=n: self.move(kind, day, n, label))
            if menu.isEmpty():
                return
            menu.exec(QCursor.pos())
            return
        for name in cells[c]:
            sub = menu.addMenu(name)
            for s in specs + [None]:
                if s == label:
                    continue
                others = self.rows_for(kind, s)[c]
                title = s or "Da assegnare"
                if others and s is not None:
                    for o in others:
                        sub.addAction(f"Scambia con {title}: {o}",
                                      lambda n=name, o=o, s=s, l=label: self.swap(kind, day, n, l, o, s))
                else:
                    sub.addAction(f"Sposta in {title}", lambda n=name, s=s: self.move(kind, day, n, s))
        menu.exec(QCursor.pos())

    def rows_for(self, kind, spec):
        for k, lab, cells in self.rows:
            if k == kind and lab == spec:
                return cells
        return [[] for _ in range(7)]

    def move(self, kind, day, name, spec):
        self.set_spec(kind, day, name, spec)
        self.fill()

    def swap(self, kind, day, a, a_spec, b, b_spec):
        self.set_spec(kind, day, a, b_spec)
        self.set_spec(kind, day, b, a_spec)
        self.fill()


def is_weekend_date(d):
    return d.weekday() >= 5


class Win(QMainWindow):
    def weekly(self):
        self.table.save()
        d = datetime.date(YEAR, MONTH, min(datetime.date.today().day, NDAYS))
        WeeklyDialog(self, d).exec()

    def prog_changed(self, _it):
        self.table.update_counters()
        if self.table.ready:
            self.table.save()

    def make_footer(self):
        f = QTableWidget(4, NDAYS + 2)
        f.horizontalHeader().hide()
        f.verticalHeader().hide()
        f.setEditTriggers(QAbstractItemView.AllEditTriggers)
        f.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        f.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        f.setFixedHeight(4 * 24 + 4)
        f.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        f.verticalHeader().setDefaultSectionSize(24)
        for c in range(NDAYS + 2):
            f.setColumnWidth(c, self.table.columnWidth(c))
        for k, label in enumerate(("SO assegnate", "SOP assegnate", "SO programmate", "SOP programmate")):
            for c in range(NDAYS + 2):
                it = QTableWidgetItem(label if c == COL_NAME else "")
                it.setTextAlignment(Qt.AlignCenter)
                it.setBackground(QBrush(QColor("#eeeeee" if k < 2 else "white")))
                if k < 2 or c in (COL_NAME, COL_TOT):
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if c == COL_NAME or c == COL_TOT:
                    it.setFont(QFont("Segoe UI", 9, QFont.Bold))
                f.setItem(k, c, it)
        return f

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva turni", f"turni_{YEAR}_{MONTH:02d}.json", "Turni (*.json)")
        if path:
            self.table.save(path)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Apri turni", os.path.dirname(save_file()), "Turni (*.json)")
        if path:
            self.table.push_undo(True)
            self.table.load(path)
            self.table.ready = True
            self.table.save()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Esporta PDF", f"turni_{YEAR}_{MONTH:02d}.pdf", "PDF (*.pdf)")
        if path:
            self.table.export_pdf(path)
            os.startfile(path)

    def clear_all(self):
        r = QMessageBox.question(
            self, "Cancella tutto",
            f"Cancellare tutti i turni di {MESI[MONTH - 1]} {YEAR}?\nPuoi annullare con Ctrl+Z.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        t = self.table
        backup(save_file(), force=True)
        t.push_undo(True)
        t.ready = False
        t.data = {}
        t.notes = {}
        CUSTOM_HOL.clear()
        t.style_headers()
        t.refresh_notes()
        self.footer.blockSignals(True)
        for k in (2, 3):
            for d in range(1, NDAYS + 1):
                self.footer.item(k, COL_FIRST + d - 1).setText("")
        self.footer.blockSignals(False)
        for i, name in enumerate(DOCTORS):
            if name:
                t.refresh_row(i)
        t.update_counters()
        t.ready = True
        t.save()

    def missing_coverage(self):
        return self.table.missing_coverage()

    def check_coverage(self):
        res = self.missing_coverage()
        if not res:
            QMessageBox.information(self, "Controllo copertura", "Tutti i turni obbligatori sono coperti.")
            return
        giorni = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
        righe = [f"{giorni[datetime.date(YEAR, MONTH, d).weekday()]} {d}: manca {', '.join(m)}"
                 for d, m in res.items()]
        box = QMessageBox(self)
        box.setWindowTitle("Controllo copertura")
        box.setText(f"{len(res)} giorni con turni mancanti.")
        box.setDetailedText("\n".join(righe))
        box.setInformativeText("\n".join(righe[:15]) + ("\n..." if len(righe) > 15 else ""))
        box.exec()

    def about(self):
        QMessageBox.about(self, "Informazioni su Moreno", ABOUT_HTML)

    def manual(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Istruzioni")
        lay = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setHtml(MANUAL_HTML)
        lay.addWidget(tb)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.resize(640, 680)
        dlg.exec()

    def summary(self):
        t = self.table
        rows = []
        for i, name in enumerate(DOCTORS):
            if not name:
                continue
            cnt = dict.fromkeys(("RG", "AG", "RN", "AN"), 0)
            fest = ass = 0
            for d in range(1, NDAYS + 1):
                e = t.entry(i, d)
                m = e.get("m")
                if m in cnt:
                    cnt[m] += 1
                if m in CONTINUABLE:
                    ass += 1
                elif t.weekend(d) and (m or e.get("p")) and m not in BLOCK:
                    fest += 1
            total, ngett = t.calc_row(i)
            rows.append((name, cnt["RG"], cnt["AG"], cnt["RN"], cnt["AN"], fest, ngett, ass, total))
        heads = ["Medico", "RG", "AG", "RN", "AN", "Sab/Dom/Fest", "Gettoni", "Assenze", "Ore", "Differenza"]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Riepilogo - {MESI[MONTH - 1]} {YEAR}")
        lay = QVBoxLayout(dlg)
        tab = QTableWidget(len(rows), len(heads))
        tab.setHorizontalHeaderLabels(heads)
        tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tab.verticalHeader().hide()
        for r, row in enumerate(rows):
            vals = [*row[:8], fmt(row[8]), fmt(row[8] - TARGET)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignCenter if c else Qt.AlignLeft | Qt.AlignVCenter)
                if c == 9 and row[8] < TARGET:
                    it.setForeground(QBrush(QColor("#e00000")))
                tab.setItem(r, c, it)
        tab.resizeColumnsToContents()
        lay.addWidget(tab)
        dlg.resize(900, 600)
        dlg.exec()

    def manage_doctors(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Gestione medici")
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        SEP = "\u2014 separatore \u2014"

        def add(name, orig):
            it = QListWidgetItem(name or SEP)
            it.setData(Qt.UserRole, name)
            it.setData(Qt.UserRole + 1, orig)
            lst.addItem(it)
            return it

        for n in DOCTORS:
            add(n, n)
        lay.addWidget(QLabel("Il separatore divide i due gruppi. Le modifiche valgono per tutti i mesi."))
        lay.addWidget(lst)

        def new():
            text, ok = QInputDialog.getText(dlg, "Nuovo medico", "Cognome:")
            if ok and text.strip():
                lst.setCurrentItem(add(text.strip(), None))

        def rename():
            it = lst.currentItem()
            if not it or not it.data(Qt.UserRole):
                return
            text, ok = QInputDialog.getText(dlg, "Rinomina", "Cognome:", text=it.data(Qt.UserRole))
            if ok and text.strip():
                it.setData(Qt.UserRole, text.strip())
                it.setText(text.strip())

        def remove():
            r = lst.currentRow()
            it = lst.currentItem()
            if it and it.data(Qt.UserRole):
                lst.takeItem(r)

        def move(delta):
            r = lst.currentRow()
            if r < 0 or not 0 <= r + delta < lst.count():
                return
            it = lst.takeItem(r)
            lst.insertItem(r + delta, it)
            lst.setCurrentRow(r + delta)

        row = QHBoxLayout()
        for label, fn in (("Aggiungi", new), ("Rinomina", rename), ("Rimuovi", remove),
                          ("\u25b2 Su", lambda: move(-1)), ("\u25bc Gi\u00f9", lambda: move(1))):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.resize(380, 600)
        if dlg.exec() != QDialog.Accepted:
            return
        self.apply_doctors([lst.item(k) for k in range(lst.count())])

    def apply_doctors(self, items):
        new_list = [it.data(Qt.UserRole) for it in items]
        names = [n for n in new_list if n]
        if len(names) != len(set(names)):
            QMessageBox.warning(self, "Gestione medici", "Ci sono nomi duplicati: modifica annullata.")
            return
        origs = {it.data(Qt.UserRole + 1) for it in items}
        renames = {it.data(Qt.UserRole + 1): it.data(Qt.UserRole) for it in items
                   if it.data(Qt.UserRole) and it.data(Qt.UserRole + 1)
                   and it.data(Qt.UserRole) != it.data(Qt.UserRole + 1)}
        removed = [n for n in DOCTORS if n and n not in origs]
        if removed and QMessageBox.question(
                self, "Gestione medici",
                "Rimuovendo " + ", ".join(removed) + " i loro turni non saranno pi\u00f9 visibili "
                "(restano nei file di backup). Continuare?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.table.save()
        backup(save_file(), force=True)
        if renames:
            for fn in os.listdir(base_dir()):
                if fn.startswith("turni_") and fn.endswith(".json"):
                    path = os.path.join(base_dir(), fn)
                    try:
                        with open(path, encoding="utf-8") as f:
                            raw = json.load(f)
                    except (OSError, ValueError):
                        continue
                    ch = False
                    for old, newn in renames.items():
                        if old in raw and newn not in raw:
                            raw[newn] = raw.pop(old)
                            ch = True
                    if ch:
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(raw, f, ensure_ascii=False, indent=1)
        DOCTORS[:] = new_list
        with open(doctors_file(), "w", encoding="utf-8") as f:
            json.dump(new_list, f, ensure_ascii=False, indent=1)
        self.build()

    def undo(self):
        if not self.table.undo():
            self.statusBar().showMessage("Niente da annullare", 3000)

    def __init__(self):
        super().__init__()
        tb = self.addToolBar("File")
        tb.addAction("Annulla (Ctrl+Z)", self.undo)
        tb.addSeparator()
        QShortcut(QKeySequence.Undo, self, self.undo)
        self.mese = QComboBox()
        self.mese.addItems(MESI)
        self.mese.setCurrentIndex(MONTH - 1)
        self.anno = QSpinBox()
        self.anno.setRange(2020, 2100)
        self.anno.setValue(YEAR)
        tb.addAction("\u25c0", lambda: self.step(-1))
        tb.addWidget(self.mese)
        tb.addWidget(self.anno)
        tb.addAction("\u25b6", lambda: self.step(1))
        tb.addSeparator()
        tb.addAction("Salva con nome", self.save_as)
        tb.addAction("Apri", self.open_file)
        tb.addAction("Esporta PDF", self.export)
        tb.addSeparator()
        tb.addAction("Controlla copertura", self.check_coverage)
        tb.addAction("Riepilogo", self.summary)
        tb.addAction("Medici", self.manage_doctors)
        tb.addAction("Cancella tutto", self.clear_all)
        tb.addSeparator()
        tb.addAction("Settimanale", self.weekly)
        tb.addAction("Istruzioni", self.manual)
        tb.addAction("Crediti", self.about)
        self.build()
        self.mese.currentIndexChanged.connect(self.pick_month)
        self.anno.valueChanged.connect(self.pick_month)
        self.resize(1500, 800)

    def pick_month(self, *_):
        set_month(self.anno.value(), self.mese.currentIndex() + 1)
        self.build()

    def step(self, delta):
        idx = self.anno.value() * 12 + self.mese.currentIndex() + delta
        self.mese.blockSignals(True)
        self.anno.blockSignals(True)
        self.anno.setValue(idx // 12)
        self.mese.setCurrentIndex(idx % 12)
        self.mese.blockSignals(False)
        self.anno.blockSignals(False)
        self.pick_month()

    def build(self):
        self.setWindowTitle(f"Moreno - U.O.C. Anestesia e Rianimazione - {MESI[MONTH - 1]} {YEAR}")
        self.table = Planner()
        self.footer = self.make_footer()
        self.table.footer = self.footer
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.table)
        lay.addWidget(self.footer)
        self.setCentralWidget(box)
        self.table.horizontalScrollBar().valueChanged.connect(self.footer.horizontalScrollBar().setValue)
        self.table.load()
        self.table.update_counters()
        self.table.ready = True
        self.footer.itemChanged.connect(self.prog_changed)
        self.statusBar().showMessage("Salvataggio automatico: " + save_file())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Win()
    if "--shot" in sys.argv:
        t = w.table
        t.assign(0, 1, "m", "SO"); t.assign(0, 1, "p", "SOP")
        t.assign(0, 2, "m", "RG"); t.assign(0, 4, "m", "RN")
        t.assign(1, 4, "m", "F"); t.assign(1, 5, "m", "F")
        t.assign(2, 2, "m", "TA"); t.assign(2, 2, "p", "P")
        t.assign(3, 6, "m", "Agg"); t.assign(3, 7, "m", "Mal")
        t.entry(0, 1)["g"] = {"p"}; t.refresh_row(0)
        w.show()
        app.processEvents()
        w.grab().save("anteprima.png")
        sys.exit(0)
    w.show()
    sys.exit(app.exec())












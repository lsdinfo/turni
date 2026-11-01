import sys
import calendar
import datetime
import os
import json
import copy
import shutil
import time
from PySide6.QtCore import Qt, QTimer, QPoint, QMarginsF, QRectF
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtGui import QPainter, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                               QMenu, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QInputDialog, QWidget, QVBoxLayout,
                               QComboBox, QSpinBox)

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
AFTERNOON = {"SOP": 6, "P": 6, "AG pom": 6}
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

UNIQUE = ("RG", "RN", "U", "AG", "AG pom")
WD = ["LU", "MA", "ME", "GIO", "VE", "SA", "DO"]
MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio",
        "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
COL_NAME, COL_FIRST = 0, 1
NDAYS = COL_TOT = 0


def set_month(y, m):
    global YEAR, MONTH, NDAYS, COL_TOT
    YEAR, MONTH = y, m
    NDAYS = calendar.monthrange(y, m)[1]
    COL_TOT = NDAYS + 1


set_month(YEAR, MONTH)
WEEKEND = QColor("#ffffa6")
SEPARATOR = QColor("#dddddd")
RED, GREEN, BLUE = QColor("#e00000"), QColor("#00a000"), QColor("#0000ff")
TEXT_COLORS = {**{k: RED for k in ("RG", "RM", "RN", "U")},
               **{k: GREEN for k in ("AG", "AG pom", "AN", "SO", "SOP", "P")},
               "TA": BLUE}


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
    return holidays(YEAR).get((MONTH, d))


def is_red(d):
    return datetime.date(YEAR, MONTH, d).weekday() == 6 or holiday_name(d) is not None


def save_file():
    return os.path.join(base_dir(), f"turni_{YEAR}_{MONTH:02d}.json")


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


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
        for d in range(1, NDAYS + 1):
            h = self.horizontalHeaderItem(COL_FIRST + d - 1)
            if is_red(d):
                h.setForeground(QBrush(QColor("#e00000")))
            if holiday_name(d):
                h.setToolTip(holiday_name(d))
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
        half = min(44, (H - title_h - head_h - 10) / (2 * n + 1))
        unit = W / (NDAYS + 2.6 + 2.0)
        xs = [0, unit * 2.6]
        for _ in range(NDAYS):
            xs.append(xs[-1] + unit)
        xs.append(xs[-1] + unit * 2.0)
        p.setPen(Qt.black)
        f = QFont("Segoe UI", 10, QFont.Bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, W, title_h), Qt.AlignLeft | Qt.AlignVCenter,
                   f"U.O.C. di Anestesia e Rianimazione - {MESI[MONTH - 1].upper()} {YEAR}")
        small = QFont("Segoe UI", 7)
        p.setFont(small)

        def cell(c, y, h, text, color=None, fg=Qt.black):
            r = QRectF(xs[c], y, xs[c + 1] - xs[c], h)
            if color:
                p.fillRect(r, color)
            p.drawRect(r)
            p.setPen(fg)
            p.drawText(r, Qt.AlignCenter, text)
            p.setPen(Qt.black)

        y = title_h
        cell(0, y, head_h, "Medico")
        for d in range(1, NDAYS + 1):
            col = WEEKEND if self.weekend(d) else None
            cell(d, y, head_h, f"{WD[datetime.date(YEAR, MONTH, d).weekday()]}\n{d}", col,
                 QColor("#e00000") if is_red(d) else Qt.black)
        cell(COL_TOT, y, head_h, "Ore")
        y += head_h
        for i, name in enumerate(DOCTORS):
            if not name:
                p.fillRect(QRectF(0, y, xs[-1], half), SEPARATOR)
                for d, text in self.notes.items():
                    cell(d, y, half, text, SEPARATOR)
                y += half
                continue
            r = i * 2
            p.setFont(f)
            cell(0, y, half * 2, name)
            p.setFont(small)
            for d in range(1, NDAYS + 1):
                if self.entry(i, d).get("m") in MERGED:
                    it = self.item(r, COL_FIRST + d - 1)
                    cell(d, y, half * 2, it.text(), it.background().color(), it.foreground().color())
                    continue
                for k in (0, 1):
                    it = self.item(r + k, COL_FIRST + d - 1)
                    cell(d, y + k * half, half, it.text(), it.background().color(), it.foreground().color())
            cell(COL_TOT, y, half * 2, self.item(r, COL_TOT).text())
            y += half * 2
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
            return [*AFTERNOON, "TA"]
        if e.get("m") in FULL or e.get("m") in BLOCK or half in e:
            return []
        opts = list(MORNING) if half == "m" else [*AFTERNOON, "TA"]
        if not e:
            opts += list(DAY_GUARD) + list(NIGHT_GUARD) + list(BLOCK)
            if d > 1 and self.entry(i, d - 1).get("m") in CONTINUABLE:
                opts.insert(0, "-")
        return opts

    def refresh_row(self, i):
        r = i * 2
        total = 0
        ngett = 0
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
        t = self.item(r, COL_TOT)
        t.setText(f"{fmt(total)} / {fmt(TARGET)}" + (f"\n{ngett} gettoni" if ngett else ""))
        t.setForeground(QBrush(QColor("#0a7d00" if total >= TARGET else "#000")))
        self.update_counters()
        if self.ready:
            self.save()

    def update_counters(self):
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
        return copy.deepcopy(self.data), dict(self.notes), prog

    def push_undo(self, with_prog=False):
        self.undo_stack.append(self.snapshot(with_prog))
        del self.undo_stack[:-100]

    def undo(self):
        if not self.undo_stack:
            return False
        data, notes, prog = self.undo_stack.pop()
        self.ready = False
        self.data, self.notes = data, notes
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
                    **{k: v for k, v in e.items() if k != "g"}, "g": set(e.get("g", []))}
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
                if e["m"] in MERGED:
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


class Win(QMainWindow):
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
        tb.addAction("Cancella tutto", self.clear_all)
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
        self.setWindowTitle(f"Turni - U.O.C. Anestesia e Rianimazione - {MESI[MONTH - 1]} {YEAR}")
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











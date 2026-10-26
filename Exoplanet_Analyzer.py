
import json
import math
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


# ============================================================
# EXOPLANET ANALYZER 3.0
# AI + NASA ATLAS + NOTES + DRAGGABLE TABS
# ============================================================

BG = "#081323"
CARD = "#122238"
TEXT = "#e8f4ff"
MUTED = "#91adc8"
BLUE = "#1687c9"
ENTRY = "#0b1a2d"
HEADER = "#183450"
ACCENT = "#52d7e8"

APP_DIR = Path(__file__).resolve().parent
NOTES_FILE = APP_DIR / "planet_notes.json"

CSV_PATH = Path.home() / "Downloads" / "world.csv"

if not CSV_PATH.exists():
    CSV_PATH = APP_DIR / "world.csv"

if not CSV_PATH.exists():
    raise SystemExit(
        "Не найден world.csv. "
        "Положи его в папку Загрузки или рядом с программой."
    )

df = pd.read_csv(
    CSV_PATH,
    comment="#",
    low_memory=False
)

if "pl_name" not in df.columns:
    raise SystemExit(
        "В CSV отсутствует столбец pl_name."
    )

df = df.dropna(subset=["pl_name"])
df = df.drop_duplicates(subset=["pl_name"])
df = df.reset_index(drop=True)

for column in [
    "pl_bmasse",
    "pl_dens",
    "pl_rade",
    "pl_eqt",
    "pl_orbper"
]:
    if column not in df.columns:
        df[column] = np.nan

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# AI MODEL
# ============================================================

training = df[
    ["pl_bmasse", "pl_dens", "pl_rade"]
].dropna()

training = training[
    (training["pl_bmasse"] > 0) &
    (training["pl_dens"] > 0) &
    (
        (training["pl_rade"] <= 1.6) |
        (training["pl_rade"] >= 2)
    )
]

model = None

if len(training) >= 10:
    targets = np.where(
        training["pl_rade"] <= 1.6,
        "Каменистая планета",
        "Газовая планета"
    )

    if len(set(targets)) == 2:
        model = RandomForestClassifier(
            n_estimators=200,
            random_state=42
        )

        model.fit(
            training[["pl_bmasse", "pl_dens"]],
            targets
        )


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()

root.title("EXOPLANET ANALYZER 4.0 — MISSION CONTROL")
root.geometry("1450x850")
root.minsize(1050, 650)
root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Space.TNotebook",
    background=BG,
    borderwidth=0
)

style.configure(
    "Space.TNotebook.Tab",
    background=CARD,
    foreground=TEXT,
    padding=(18, 12),
    borderwidth=0,
    font=("Segoe UI", 10, "bold")
)

style.map(
    "Space.TNotebook.Tab",
    background=[("selected", "#1c5279"), ("active", "#24435f")],
    foreground=[("selected", "#e6faff"), ("active", "white")]
)

tk.Frame(root, bg=ACCENT, height=2).pack(fill="x")

topbar = tk.Frame(root, bg=BG)
topbar.pack(fill="x", padx=12, pady=(10, 0))

tk.Label(
    topbar,
    text="✦ EXOPLANET ANALYZER  /  MISSION CONTROL",
    bg=BG,
    fg=ACCENT,
    font=("Segoe UI", 13, "bold")
).pack(side="left", padx=8)

tk.Label(
    topbar,
    text="NASA EXOPLANET RESEARCH  •  AI ANALYSIS  •  SKY MAP",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 9)
).pack(side="left", padx=16)

notebook = ttk.Notebook(
    root,
    style="Space.TNotebook"
)

notebook.pack(
    fill="both",
    expand=True,
    padx=12,
    pady=10
)


def make_button(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=BLUE,
        fg="white",
        activebackground="#2ca8e5",
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        padx=12,
        pady=8
    )


def make_label(parent, text, size=11, color=TEXT):
    return tk.Label(
        parent,
        text=text,
        bg=CARD,
        fg=color,
        font=("Segoe UI", size)
    )


def fmt(value):
    if value is None:
        return "Нет данных"

    try:
        if pd.isna(value):
            return "Нет данных"
    except (ValueError, TypeError):
        pass

    if isinstance(value, (float, int, np.number)):
        return f"{value:.6g}"

    value = str(value).strip()
    return value if value else "Нет данных"


def nasa_link(name):
    return (
        "https://exoplanetarchive.ipac.caltech.edu/overview/"
        + quote(str(name), safe="")
    )


def get_field(row, field):
    return row[field] if field in row.index else None


# ============================================================
# СВОБОДНЫЕ ПАНЕЛИ ВНУТРИ ГЛАВНОГО ОКНА
# Вкладки остаются прежними; отцепленная вкладка становится
# перемещаемой панелью с изменяемым размером.
# ============================================================

floating_tabs = {}
drag_start = None
drag_origin = None


def tab_at(x, y):
    try:
        return notebook.index(f"@{x},{y}")
    except tk.TclError:
        return None


def dock_tab(tab):
    key = str(tab)
    info = floating_tabs.get(key)
    if not info:
        return
    if info.get("kind") == "star_map":
        info["panel"].destroy()
        floating_tabs.pop(key, None)
        notebook.add(tab, text="  ✦ ЗВЁЗДНАЯ КАРТА  ")
        star_map_view.refresh_map()
        notebook.select(tab)
        return
    note_id = info["note_id"]
    data = note_tabs[note_id]
    # Переносим набранный текст из свободной панели в обычную вкладку.
    title = data["title"].get()
    content = data["editor"].get("1.0", "end-1c")
    data["original_title"].delete(0, tk.END)
    data["original_title"].insert(0, title)
    data["original_editor"].delete("1.0", tk.END)
    data["original_editor"].insert("1.0", content)
    data["title"] = data.pop("original_title")
    data["editor"] = data.pop("original_editor")
    floating_tabs.pop(key, None)
    info["panel"].destroy()
    notebook.add(tab, text=f"  📝 {title[:16]}  ")
    notebook.select(tab)
    save_note(note_id, quiet=True)


def float_tab(tab, x=80, y=80):
    if isinstance(tab, str):
        tab = root.nametowidget(tab)
    if str(tab) in floating_tabs:
        return

    if tab == star_map_tab:
        float_star_map(tab, x, y)
        return

    # Свободные панели доступны только для заметок.
    note_id = next(
        (nid for nid, data in note_tabs.items() if data["frame"] == tab),
        None
    )
    if note_id is None:
        messagebox.showinfo(
            "Свободная панель",
            "Перемещение и изменение размера доступны для заметок и звёздной карты."
        )
        return

    data = note_tabs[note_id]
    title = data["title"].get()
    content = data["editor"].get("1.0", "end-1c")

    # Не перемещаем саму вкладку Tkinter: создаём редактируемую
    # панель поверх приложения, а содержимое синхронизируем.
    notebook.forget(tab)
    root.update_idletasks()
    width = min(650, max(340, root.winfo_width() - 50))
    height = min(490, max(270, root.winfo_height() - 100))
    x = max(0, min(x, root.winfo_width() - width))
    y = max(45, min(y + 45, root.winfo_height() - height))

    panel = tk.Frame(root, bg=CARD, highlightbackground=BLUE,
                     highlightthickness=2)
    panel.place(x=x, y=y, width=width, height=height)
    panel.lift()

    header = tk.Frame(panel, bg=HEADER, height=35, cursor="fleur")
    header.pack(fill="x")
    header.pack_propagate(False)
    drag_label = tk.Label(header, text="  ⠿  📝 ЗАМЕТКА",
                          bg=HEADER, fg=TEXT, cursor="fleur")
    drag_label.pack(side="left", fill="y")
    tk.Button(header, text="↩ ВО ВКЛАДКИ", bg=BLUE, fg="white",
              relief="flat", command=lambda: dock_tab(tab)).pack(
                  side="right", padx=5, pady=3)

    body = tk.Frame(panel, bg=CARD)
    body.pack(fill="both", expand=True, padx=10, pady=(8, 0))
    title_entry = tk.Entry(body, bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                           relief="flat", font=("Segoe UI", 12, "bold"))
    title_entry.insert(0, title)
    title_entry.pack(fill="x", ipady=6, pady=(0, 8))

    editor = tk.Text(body, bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                     relief="flat", wrap="word", undo=True,
                     font=("Consolas", 11))
    editor.insert("1.0", content)
    editor.pack(fill="both", expand=True)

    bottom = tk.Frame(panel, bg=CARD)
    bottom.pack(fill="x", padx=10, pady=6)
    make_button(bottom, "💾 СОХРАНИТЬ",
                lambda: save_note(note_id)).pack(side="left")

    grip = tk.Label(panel, text="◢", bg=BLUE, fg="white",
                    cursor="bottom_right_corner", font=("Segoe UI", 13))
    grip.place(relx=1, rely=1, anchor="se", width=26, height=26)

    data["original_title"] = data["title"]
    data["original_editor"] = data["editor"]
    data["title"] = title_entry
    data["editor"] = editor
    floating_tabs[str(tab)] = {
        "panel": panel, "note_id": note_id, "title": title
    }

    move = {}
    def start_move(e):
        panel.lift()
        move.update(mx=e.x_root, my=e.y_root,
                    px=panel.winfo_x(), py=panel.winfo_y())

    def do_move(e):
        if "mx" not in move:
            return
        nx = move["px"] + e.x_root - move["mx"]
        ny = move["py"] + e.y_root - move["my"]
        nx = max(0, min(nx, root.winfo_width() - 100))
        ny = max(38, min(ny, root.winfo_height() - 45))
        panel.place_configure(x=nx, y=ny)

    for target in (header, drag_label):
        target.bind("<ButtonPress-1>", start_move)
        target.bind("<B1-Motion>", do_move)

    # Сглаживание: не перестраиваем вложенные Tk-виджеты на каждое
    # событие мыши. Применяем только последний размер раз в ~16 мс.
    resize = {"active": False, "job": None, "pending": None}

    def apply_resize():
        resize["job"] = None
        if not resize["active"] or resize["pending"] is None:
            return
        w, h = resize["pending"]
        resize["pending"] = None
        panel.place_configure(width=w, height=h)

    def start_resize(e):
        panel.lift()
        if resize["job"] is not None:
            panel.after_cancel(resize["job"])
            resize["job"] = None
        resize.update(active=True, mx=e.x_root, my=e.y_root,
                      w=panel.winfo_width(), h=panel.winfo_height(),
                      pending=None)

    def do_resize(e):
        if not resize["active"]:
            return
        w = max(290, resize["w"] + e.x_root - resize["mx"])
        h = max(220, resize["h"] + e.y_root - resize["my"])
        w = min(w, max(290, root.winfo_width() - panel.winfo_x()))
        h = min(h, max(220, root.winfo_height() - panel.winfo_y()))
        resize["pending"] = (int(w), int(h))
        if resize["job"] is None:
            resize["job"] = panel.after(16, apply_resize)

    def stop_resize(e):
        if not resize["active"]:
            return
        # Последний размер применяем сразу при отпускании мыши.
        do_resize(e)
        if resize["job"] is not None:
            panel.after_cancel(resize["job"])
            resize["job"] = None
        if resize["pending"] is not None:
            w, h = resize["pending"]
            panel.place_configure(width=w, height=h)
        resize["pending"] = None
        resize["active"] = False

    grip.bind("<ButtonPress-1>", start_resize)
    grip.bind("<B1-Motion>", do_resize)
    grip.bind("<ButtonRelease-1>", stop_resize)


def start_tab_drag(event):
    global drag_start, drag_origin
    drag_start = tab_at(event.x, event.y)
    drag_origin = (event.x, event.y)


def finish_tab_drag(event):
    global drag_start, drag_origin
    if drag_start is None:
        return
    tabs = notebook.tabs()
    if drag_start >= len(tabs):
        drag_start = None
        return
    moving_tab = tabs[drag_start]
    target = tab_at(event.x, event.y)
    if target is not None and target != drag_start:
        notebook.insert(target, moving_tab)
        notebook.select(moving_tab)
    elif target is None and drag_origin is not None:
        # Вытаскиваем вкладку вниз с полосы заголовков.
        if event.y > drag_origin[1] + 35:
            float_tab(moving_tab, event.x - 180, event.y - 20)
    drag_start = None
    drag_origin = None


notebook.bind("<ButtonPress-1>", start_tab_drag)
notebook.bind("<ButtonRelease-1>", finish_tab_drag)

# ============================================================
# NOTES STORAGE
# ============================================================

notes = {}

if NOTES_FILE.exists():
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict):
            notes = loaded

    except (OSError, json.JSONDecodeError):
        messagebox.showwarning(
            "Блокнот",
            "Не удалось прочитать сохранённые заметки."
        )

note_tabs = {}
planet_tabs = {}


def save_notes():
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(
            notes,
            f,
            ensure_ascii=False,
            indent=2
        )


def close_tab(tab):
    if str(tab) in [str(ai_tab), str(atlas_tab), str(star_map_tab)]:
        return

    for name, frame in list(planet_tabs.items()):
        if frame == tab:
            planet_tabs.pop(name, None)

    for note_id, data in list(note_tabs.items()):
        if data["frame"] == tab:
            save_note(note_id, quiet=True)
            note_tabs.pop(note_id, None)

    if str(tab) in floating_tabs:
        dock_tab(tab)
    notebook.forget(tab)
    tab.destroy()


# ============================================================
# NOTE TABS
# ============================================================

def save_note(note_id, quiet=False):
    if note_id not in note_tabs:
        return

    data = note_tabs[note_id]

    title = data["title"].get().strip()
    content = data["editor"].get("1.0", "end-1c")

    if not title:
        title = "Без названия"

    notes[note_id] = {
        "title": title,
        "text": content,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    try:
        save_notes()
    except OSError as error:
        messagebox.showerror(
            "Ошибка сохранения",
            str(error)
        )
        return

    if str(data["frame"]) in floating_tabs:
        floating_tabs[str(data["frame"])]["title"] = f"  📝 {title[:16]}  "
    else:
        notebook.tab(
            data["frame"],
            text=f"  📝 {title[:16]}  "
        )

    if not quiet:
        messagebox.showinfo(
            "Блокнот",
            "Заметка сохранена!"
        )


def create_note(
    note_id=None,
    title="Новая заметка",
    content=""
):
    if note_id is None:
        note_id = uuid.uuid4().hex

    if note_id in note_tabs:
        existing = note_tabs[note_id]["frame"]
        if str(existing) in floating_tabs:
            floating_tabs[str(existing)]["panel"].lift()
        else:
            notebook.select(existing)
        return

    tab = tk.Frame(notebook, bg=CARD)

    notebook.add(
        tab,
        text=f"  📝 {title[:16]}  "
    )

    note_tabs[note_id] = {
        "frame": tab
    }

    header = tk.Frame(tab, bg=CARD)
    header.pack(fill="x", padx=20, pady=15)

    make_label(
        header,
        "НАУЧНЫЙ БЛОКНОТ",
        17,
        TEXT
    ).pack(side="left")

    make_button(
        header,
        "× ЗАКРЫТЬ",
        lambda: close_tab(tab)
    ).pack(side="right")

    make_label(
        tab,
        "Название заметки",
        11,
        MUTED
    ).pack(anchor="w", padx=22)

    title_entry = tk.Entry(
        tab,
        bg=ENTRY,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Segoe UI", 14, "bold")
    )

    title_entry.insert(0, title)
    title_entry.pack(
        fill="x",
        padx=22,
        pady=(5, 18),
        ipady=9
    )

    editor_frame = tk.Frame(tab, bg=CARD)
    editor_frame.pack(
        fill="both",
        expand=True,
        padx=22
    )

    editor = tk.Text(
        editor_frame,
        bg=ENTRY,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Consolas", 12),
        wrap="word",
        undo=True,
        padx=16,
        pady=16
    )

    scrollbar = ttk.Scrollbar(
        editor_frame,
        command=editor.yview
    )

    editor.configure(
        yscrollcommand=scrollbar.set
    )

    scrollbar.pack(side="right", fill="y")
    editor.pack(
        side="left",
        fill="both",
        expand=True
    )

    editor.insert("1.0", content)

    note_tabs[note_id].update({
        "title": title_entry,
        "editor": editor
    })

    footer = tk.Frame(tab, bg=CARD)
    footer.pack(fill="x", padx=22, pady=15)

    make_button(
        footer,
        "💾 СОХРАНИТЬ",
        lambda: save_note(note_id)
    ).pack(side="left", padx=(0, 10))

    def delete_this_note():
        if not messagebox.askyesno(
            "Удалить",
            "Удалить эту заметку навсегда?"
        ):
            return

        notes.pop(note_id, None)

        try:
            save_notes()
        except OSError as error:
            messagebox.showerror(
                "Ошибка",
                str(error)
            )
            return

        note_tabs.pop(note_id, None)
        if str(tab) in floating_tabs:
            dock_tab(tab)
        notebook.forget(tab)
        tab.destroy()

    make_button(
        footer,
        "УДАЛИТЬ",
        delete_this_note
    ).pack(side="left")

    notebook.select(tab)


def save_current_note(event=None):
    current = notebook.select()

    for note_id, data in note_tabs.items():
        if str(data["frame"]) == current:
            save_note(note_id, quiet=True)
            return "break"


root.bind("<Control-s>", save_current_note)


# ============================================================
# PLUS BUTTON
# ============================================================

make_button(
    topbar,
    "＋ НОВАЯ ВКЛАДКА",
    create_note
).pack(side="right", padx=6)


make_button(
    topbar,
    "▣ ОТЦЕПИТЬ ВКЛАДКУ",
    lambda: float_tab(notebook.select(), 90, 65) if notebook.select() else None
).pack(side="right", padx=6)


# ============================================================
# PLANET DOSSIER
# ============================================================

PLANET_FIELDS = [
    ("pl_name", "Название планеты"),
    ("hostname", "Звезда"),
    ("pl_bmasse", "Масса (Земля = 1)"),
    ("pl_rade", "Радиус (Земля = 1)"),
    ("pl_dens", "Плотность (г/см³)"),
    ("pl_eqt", "Температура равновесия (K)"),
    ("pl_orbper", "Орбитальный период (сутки)"),
    ("pl_orbsmax", "Большая полуось (а.е.)"),
    ("pl_orbeccen", "Эксцентриситет"),
    ("pl_orbincl", "Наклонение орбиты"),
    ("sy_dist", "Расстояние (парсек)"),
    ("sy_pnum", "Число планет в системе"),
    ("st_spectype", "Тип звезды"),
    ("st_teff", "Температура звезды (K)"),
    ("st_mass", "Масса звезды"),
    ("st_rad", "Радиус звезды"),
    ("st_age", "Возраст звезды"),
    ("disc_year", "Год открытия"),
    ("discoverymethod", "Метод открытия"),
    ("disc_facility", "Обсерватория"),
    ("disc_telescope", "Телескоп")
]


projection_tabs = {}

def open_3d_projection(name):
    """NASA planet detail -> separate interactive 3D projection tab."""
    name=str(name)
    existing=projection_tabs.get(name)
    if existing is not None and existing.winfo_exists():
        notebook.select(existing); return
    matches=df[df["pl_name"]==name]
    if matches.empty:return
    data=matches.iloc[0]
    tab=tk.Frame(notebook,bg=CARD)
    projection_tabs[name]=tab
    notebook.add(tab,text=f"  ◉ 3D {name[:14]}  ")
    top=tk.Frame(tab,bg=CARD)
    top.pack(fill="x",padx=15,pady=12)
    make_label(top,f"3D-ПРОЕКЦИЯ  /  {name}",17).pack(side="left")
    def close_projection():
        projection_tabs.pop(name,None)
        notebook.forget(tab);tab.destroy()
    make_button(top,"× ЗАКРЫТЬ",close_projection).pack(side="right")
    viewer=make_sphere_view(tab)
    viewer.pack(fill="both",expand=True,padx=15,pady=6)
    def num(key,default):
        try:
            value=float(data.get(key,default))
            return value if math.isfinite(value) else default
        except (ValueError,TypeError):return default
    density=num("pl_dens",5.51)
    temp=num("pl_eqt",288)-273.15
    state=viewer.planet_state
    state["type"]="gas" if density<2 else ("hot" if temp>100 else "rock")
    state["ready"]=True
    viewer.planet_redraw()
    details=(f"Масса: {fmt(data.get('pl_bmasse'))} M⊕    •    "
             f"Радиус: {fmt(data.get('pl_rade'))} R⊕    •    "
             f"Плотность: {fmt(data.get('pl_dens'))} г/см³")
    tk.Label(tab,text=details,bg=CARD,fg=TEXT,font=("Segoe UI",11)).pack(pady=5)
    tk.Label(tab,text="Условная художественная 3D-модель по данным NASA, не фотография.",
             bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(pady=(0,12))
    notebook.select(tab)

def open_planet(name):
    name = str(name)

    if name in planet_tabs:
        notebook.select(planet_tabs[name])
        return

    matches = df[df["pl_name"] == name]

    if matches.empty:
        messagebox.showwarning(
            "NASA",
            "Планета не найдена."
        )
        return

    planet = matches.iloc[0]

    tab = tk.Frame(notebook, bg=CARD)
    planet_tabs[name] = tab

    notebook.add(
        tab,
        text=f"  🌍 {name[:18]}  "
    )

    header = tk.Frame(tab, bg=CARD)
    header.pack(fill="x", padx=20, pady=15)

    make_label(
        header,
        name,
        20
    ).pack(side="left")

    make_button(
        header,
        "× ЗАКРЫТЬ",
        lambda: close_tab(tab)
    ).pack(side="right", padx=5)

    make_button(
        header,
        "NASA ↗",
        lambda: webbrowser.open(nasa_link(name))
    ).pack(side="right", padx=5)

    make_button(header,"◉ ПОДРОБНЕЕ: 3D",
                lambda n=name: open_3d_projection(n)).pack(side="right",padx=5)

    def send_to_notes():
        text = (
            f"ПЛАНЕТА: {name}\n\n"
            + "\n".join(
                f"{description}: {fmt(get_field(planet, key))}"
                for key, description in PLANET_FIELDS
            )
            + f"\n\nNASA: {nasa_link(name)}"
            + "\n\nМОИ НАБЛЮДЕНИЯ:\n"
        )

        create_note(
            title=name,
            content=text
        )

    make_button(
        header,
        "📝 В БЛОКНОТ",
        send_to_notes
    ).pack(side="right", padx=5)

    outer = tk.Frame(tab, bg=CARD)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(
        outer,
        bg=CARD,
        highlightthickness=0
    )

    scroll = ttk.Scrollbar(
        outer,
        command=canvas.yview
    )

    body = tk.Frame(canvas, bg=CARD)

    window = canvas.create_window(
        (0, 0),
        window=body,
        anchor="nw"
    )

    body.bind(
        "<Configure>",
        lambda event: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(
            window,
            width=event.width
        )
    )

    canvas.configure(
        yscrollcommand=scroll.set
    )

    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    make_label(
        body,
        "ДАННЫЕ NASA EXOPLANET ARCHIVE",
        15,
        BLUE
    ).pack(anchor="w", padx=25, pady=18)

    for key, description in PLANET_FIELDS:
        line = tk.Frame(body, bg=CARD)
        line.pack(fill="x", padx=25, pady=5)

        make_label(
            line,
            description,
            11,
            MUTED
        ).pack(side="left")

        value = fmt(get_field(planet, key))

        tk.Label(
            line,
            text=value,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            wraplength=450,
            justify="right"
        ).pack(side="right")

    make_label(
        body,
        "ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ NASA",
        14,
        BLUE
    ).pack(anchor="w", padx=25, pady=(25, 10))

    used = {key for key, _ in PLANET_FIELDS}

    for key in planet.index:
        if key in used:
            continue

        value = planet[key]

        try:
            if pd.isna(value):
                continue
        except (ValueError, TypeError):
            continue

        line = tk.Frame(body, bg=CARD)
        line.pack(fill="x", padx=25, pady=3)

        make_label(
            line,
            key,
            10,
            MUTED
        ).pack(side="left")

        tk.Label(
            line,
            text=fmt(value),
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10),
            wraplength=450,
            justify="right"
        ).pack(side="right")

    notebook.select(tab)


# ============================================================
# AI TAB
# ============================================================

ai_tab = tk.Frame(notebook, bg=BG)
notebook.add(ai_tab, text="  ✦ AI-АНАЛИЗ  ")

left = tk.Frame(
    ai_tab,
    bg=CARD,
    padx=18,
    pady=18
)

left.pack(
    side="left",
    fill="y",
    padx=5,
    pady=5
)

make_label(
    left,
    "ПАРАМЕТРЫ ПЛАНЕТЫ",
    14
).pack(anchor="w", pady=(0, 15))

entries = []

for field_name, default in [
    ("Масса (Земля = 1)", "1"),
    ("Плотность (г/см³)", "5.51"),
    ("Температура (°C)", "15"),
    ("Год (сутки)", "365.25")
]:
    make_label(
        left,
        field_name,
        10,
        MUTED
    ).pack(anchor="w", pady=(10, 5))

    entry = tk.Entry(
        left,
        bg=ENTRY,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Segoe UI", 12),
        width=23
    )

    entry.insert(0, default)
    entry.pack(fill="x", ipady=8)
    entries.append(entry)

center = tk.Frame(
    ai_tab,
    bg=CARD,
    padx=16,
    pady=18
)

center.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5,
    pady=5
)

make_label(
    center,
    "РЕЗУЛЬТАТ AI",
    15
).pack(anchor="w")

result_var = tk.StringVar(
    value="Введи параметры планеты и нажми АНАЛИЗ."
)

tk.Label(
    center,
    textvariable=result_var,
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 11),
    wraplength=350,
    justify="left",
    anchor="nw"
).pack(fill="both", expand=True, pady=15)

right = tk.Frame(
    ai_tab,
    bg=CARD,
    padx=10,
    pady=18
)

right.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5,
    pady=5
)

make_label(right, "3D-ПЛАНЕТА", 15).pack(anchor="w")

# The viewer stays empty until a successful AI analysis.
# Cached coordinate grid: avoids recreating it during each mouse movement.
from PIL import Image, ImageTk
_SPHERE_GRID = {}

def sphere_image(state, n):
    """Vectorized, light-weight software sphere. No animation loop."""
    if n not in _SPHERE_GRID:
        yy, xx = np.mgrid[-1:1:complex(n), -1:1:complex(n)]
        rr = (xx / .91) ** 2 + (yy / .91) ** 2
        _SPHERE_GRID[n] = (xx/.91, -yy/.91, np.sqrt(np.clip(1-rr,0,1)), rr<=1)
    vx, vy, vz, inside = _SPHERE_GRID[n]
    a, t = state["angle"], state["tilt"]
    xr = vx*np.cos(a)+vz*np.sin(a)
    zr = -vx*np.sin(a)+vz*np.cos(a)
    yr = vy*np.cos(t)-zr*np.sin(t)
    zz = vy*np.sin(t)+zr*np.cos(t)
    lat = np.arcsin(np.clip(yr,-1,1)); lon = np.arctan2(xr,zz)
    if state["type"] == "gas":
        bands = np.sin(lat*29+1.5*np.sin(lon*3)+.35*np.sin(lon*11+lat*9))
        storm = np.exp(-((lat+.16)**2/.013+(np.sin(lon-.5))**2/.032))
        base = np.stack((169+38*bands+33*storm,
                         119+31*bands+19*storm,
                         87+24*bands),axis=-1)
    else:
        terrain = (np.sin(lon*6+np.cos(lat*9))*np.cos(lat*11-lon*2)
                   +.42*np.sin(lon*19+lat*13)+.18*np.sin(lon*43-lat*31))
        land = terrain > .16
        if state["type"] == "rock":
            ice = np.abs(lat)>1.28
            base=np.stack((np.where(ice,214,np.where(land,107,25)),
                           np.where(ice,224,np.where(land,144,77)),
                           np.where(ice,234,np.where(land,103,155))),axis=-1)
        else:
            base=np.stack((np.where(land,170,96),np.where(land,105,62),
                           np.where(land,72,54)),axis=-1)
    diffuse=np.clip(vx*(-.48)+vy*.24+vz*.84,0,1)
    light=.13+.88*diffuse
    spec=np.maximum(0, vx*(-.48)+vy*.24+vz*.84)**18 * 18
    rgb=np.clip(base*light[...,None]+spec[...,None],0,255).astype(np.uint8)
    alpha=np.where(inside,255,0).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,alpha)),"RGBA")

def make_sphere_view(parent, initial=None):
    """Reusable 3D viewer for AI and NASA dossiers."""
    cv=tk.Canvas(parent,bg=ENTRY,highlightthickness=0,cursor="fleur")
    st={"ready":False,"type":"rock","angle":.35,"tilt":.18,"zoom":1.,
        "drag":None,"job":None,"quality_job":None,"image":None,"moving":False}
    if initial: st.update(initial)
    def draw():
        st["job"]=None
        if not st["ready"] or not cv.winfo_exists(): return
        w,h=cv.winfo_width(),cv.winfo_height()
        if w<60 or h<60:return
        # 110px during drag, 250px after release: interactive and sharp.
        n=72 if st["moving"] else 250
        im=sphere_image(st,n)
        d=max(75,min(300 if st["moving"] else 460,int(min(w,h)*.74*st["zoom"])))
        im=im.resize((d,d),Image.Resampling.BILINEAR)
        st["image"]=ImageTk.PhotoImage(im)
        cv.delete("all")
        cv.create_image(w//2,h//2,image=st["image"])
        cv.create_text(w//2,h-17,text="Зажми ЛКМ — вращение  •  Колесо — масштаб",
                       fill=MUTED,font=("Segoe UI",9))
    def schedule(delay=25):
        # IMPORTANT: do not cancel an already scheduled frame on every mouse event.
        # Otherwise fast dragging postpones drawing until the mouse stops.
        if not st["ready"] or st["job"] is not None:
            return
        st["job"] = cv.after(delay, draw)
    def down(e):
        st["drag"] = (e.x, e.y) if st["ready"] else None
    def motion(e):
        if st["drag"] is None:
            return
        x, y = st["drag"]
        st["angle"] += (e.x-x)*.012
        st["tilt"] = max(-1.2, min(1.2, st["tilt"]+(e.y-y)*.008))
        st["drag"] = (e.x, e.y)
        st["moving"] = True
        schedule(1)
    def release(e):
        st["drag"] = None
        st["moving"] = False
        # A pending low-quality frame will read the updated moving flag.
        schedule(1)
    def wheel(e):
        if not st["ready"]:
            return
        st["zoom"] = max(.80, min(1.45, st["zoom"]*(1.1 if e.delta>0 else 1/1.1)))
        schedule(1)
    cv.bind("<ButtonPress-1>",down)
    cv.bind("<B1-Motion>",motion)
    cv.bind("<ButtonRelease-1>",release)
    cv.bind("<MouseWheel>",wheel)
    cv.bind("<Configure>",lambda e:schedule(100))
    cv.planet_state=st
    cv.planet_redraw=schedule
    return cv

planet_view=make_sphere_view(right)
planet_view.pack(fill="both",expand=True,pady=(12,0))
planet_state=planet_view.planet_state


def show_planet(mass, density, temp, predicted):
    # A scientific illustration, not a measured appearance of an exoplanet.
    name = str(predicted).lower()
    if "газ" in name or density < 2:
        planet_state["type"] = "gas"
    elif temp > 100:
        planet_state["type"] = "hot"
    else:
        planet_state["type"] = "rock"
    planet_state["ready"] = True
    planet_state["angle"] = 0.35
    planet_state["tilt"] = 0.18
    planet_state["zoom"] = 1.0
    planet_view.planet_redraw()


# ============================================================
# PLANET DATA FOR MAPS
# ============================================================

plot_data = df.dropna(
    subset=["pl_bmasse", "pl_dens"]
)

plot_data = plot_data[
    (plot_data["pl_bmasse"] > 0) &
    (plot_data["pl_bmasse"] <= 100) &
    (plot_data["pl_dens"] > 0) &
    (plot_data["pl_dens"] <= 20)
].reset_index(drop=True)


def mission_plot_style(ax, fig):
    """Consistent dark Mission Control plot styling; no data changes."""
    fig.patch.set_facecolor(CARD)
    ax.set_facecolor(ENTRY)
    ax.tick_params(axis="both", colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#29445d")
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(ACCENT)
    ax.grid(True, color="#2d526a", alpha=0.38, linewidth=0.7)
    ax.set_axisbelow(True)
    legend = ax.get_legend()
    if legend is not None:
        legend.get_frame().set_facecolor("#152b43")
        legend.get_frame().set_edgecolor("#3a617c")
        for label in legend.get_texts():
            label.set_color(TEXT)


def draw_ai(mass=None, density=None, analog=None):
    """Compatibility wrapper: AI visualization now shows a 3D sphere."""
    if mass is not None and density is not None:
        show_planet(mass, density, 15, "Каменистая")



# ============================================================
# EASTER EGGS
# ============================================================

SECRETS = {
    (1, 5.51, 15, 365.25): "HOME SWEET HOME",
    (0.107, 3.93, -63, 687): "MARS DETECTED",
    (42, 5.9, -17, 314.1): "DON'T PANIC",
    (13.7, 8.2, -113, 666): "UNKNOWN SIGNAL",
    (4.04, 7.7, 404, 88): "PLANET 404",
    (7.21, 3.14, -77, 777): "INVERTED UNIVERSE",
    (9.81, 6.67, -273.15, 299.792): "DEBUG MODE",
    (23, 19, -84, 2001): "WE HAVE BEEN WATCHING"
}

found_secrets = set()


def check_secrets(values):
    for combination, message in SECRETS.items():
        if all(
            abs(a - b) < 0.0001
            for a, b in zip(values, combination)
        ):
            found_secrets.add(message)

            messagebox.showinfo(
                "SECRET FOUND",
                message
            )

            if message == "INVERTED UNIVERSE":
                result_var.set(
                    "СИГНАЛ ИЗ ДРУГОЙ ВСЕЛЕННОЙ\n"
                    "РЕАЛЬНОСТЬ НЕСТАБИЛЬНА"
                )

            if len(found_secrets) == len(SECRETS):
                messagebox.showinfo(
                    "EXPLORER",
                    "ВСЕ СЕКРЕТЫ ОБНАРУЖЕНЫ!"
                )

            return True

    return False


# ============================================================
# ANALYSIS
# ============================================================

def analyze():
    try:
        values = [
            float(entry.get().replace(",", "."))
            for entry in entries
        ]

        if not all(math.isfinite(x) for x in values):
            raise ValueError

    except ValueError:
        messagebox.showerror(
            "Ошибка",
            "Введи четыре правильных числа."
        )
        return

    mass, density, temp, year = values

    if check_secrets(values):
        return

    if mass <= 0 or density <= 0 or year <= 0:
        messagebox.showerror(
            "Ошибка",
            "Масса, плотность и год должны быть положительными."
        )
        return

    if model is not None:
        features = pd.DataFrame(
            [[mass, density]],
            columns=["pl_bmasse", "pl_dens"]
        )

        planet_type = model.predict(features)[0]

        confidence = max(
            model.predict_proba(features)[0]
        ) * 100

        prediction = (
            f"{planet_type}\n"
            f"Уверенность: {confidence:.1f}%"
        )
    else:
        prediction = "Недостаточно данных для AI"

    scores = [
        max(0, 1 - abs(mass - 1) / max(mass, 1)),
        max(0, 1 - abs(density - 5.51) / max(density, 5.51)),
        max(0, 1 - abs(temp - 15) / 100),
        max(0, 1 - abs(year - 365.25) / max(year, 365.25))
    ]

    similarity = sum(scores) * 25

    valid = plot_data

    analog = None

    if not valid.empty:
        distances = (
            ((valid["pl_bmasse"] - mass) / mass) ** 2 +
            ((valid["pl_dens"] - density) / density) ** 2
        )

        analog = valid.loc[distances.idxmin()]

    text = (
        f"ТИП ПЛАНЕТЫ\n{prediction}\n\n"
        f"ПОХОЖЕСТЬ НА ЗЕМЛЮ\n{similarity:.1f}%\n\n"
    )

    if analog is not None:
        text += (
            f"БЛИЖАЙШИЙ АНАЛОГ NASA\n"
            f"{analog['pl_name']}\n\n"
            f"Масса: {fmt(analog['pl_bmasse'])}\n"
            f"Плотность: {fmt(analog['pl_dens'])}\n\n"
            f"Нажми кнопку «ОТКРЫТЬ АНАЛОГ»."
        )

        analog_button.configure(
            state="normal",
            command=lambda n=analog["pl_name"]: open_planet(n)
        )
    else:
        analog_button.configure(state="disabled")

    text += (
        "\n\nОценка похожести условная, "
        "это не научная вероятность обитаемости."
    )

    result_var.set(text)
    show_planet(mass, density, temp, prediction)


def clear_fields():
    for entry in entries:
        entry.delete(0, tk.END)

    result_var.set("Поля очищены.")
    analog_button.configure(state="disabled")
    planet_state["ready"] = False
    planet_view.delete("all")


make_button(
    left,
    "АНАЛИЗИРОВАТЬ",
    analyze
).pack(fill="x", pady=(25, 8))

make_button(
    left,
    "ОЧИСТИТЬ",
    clear_fields
).pack(fill="x", pady=6)

analog_button = make_button(
    left,
    "ОТКРЫТЬ АНАЛОГ",
    lambda: None
)

analog_button.configure(state="disabled")
analog_button.pack(fill="x", pady=6)

draw_ai()


# ============================================================
# NASA ATLAS
# ============================================================

atlas_tab = tk.Frame(notebook, bg=CARD)
notebook.add(atlas_tab, text="  🌌 АТЛАС NASA  ")

searchbar = tk.Frame(atlas_tab, bg=CARD)
searchbar.pack(fill="x", padx=15, pady=12)

make_label(
    searchbar,
    "ПОИСК:",
    12
).pack(side="left", padx=8)

search_entry = tk.Entry(
    searchbar,
    bg=ENTRY,
    fg=TEXT,
    insertbackground=TEXT,
    relief="flat",
    font=("Segoe UI", 12)
)

search_entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=8
)

atlas_body = tk.PanedWindow(
    atlas_tab,
    orient="horizontal",
    bg=BG,
    sashwidth=7
)

atlas_body.pack(
    fill="both",
    expand=True,
    padx=12,
    pady=12
)

map_panel = tk.Frame(atlas_body, bg=CARD)
list_panel = tk.Frame(atlas_body, bg=CARD)

atlas_body.add(map_panel, minsize=400)
atlas_body.add(list_panel, minsize=280)

fig_atlas = Figure(figsize=(7, 5), dpi=100, facecolor=CARD)
ax_atlas = fig_atlas.add_subplot(111)

canvas_atlas = FigureCanvasTkAgg(
    fig_atlas,
    master=map_panel
)

canvas_atlas.get_tk_widget().pack(
    fill="both",
    expand=True
)

toolbar = NavigationToolbar2Tk(
    canvas_atlas,
    map_panel,
    pack_toolbar=False
)

toolbar.update()
toolbar.pack(fill="x")

make_label(
    list_panel,
    "НАЙДЕННЫЕ ПЛАНЕТЫ  /  NASA CATALOG",
    13
).pack(anchor="w", padx=12, pady=12)

planet_list = tk.Listbox(
    list_panel,
    bg=ENTRY,
    fg=TEXT,
    selectbackground=BLUE,
    relief="flat",
    font=("Segoe UI", 11)
)

planet_list.pack(
    fill="both",
    expand=True,
    padx=12,
    pady=5
)

shown = plot_data.copy()


def update_atlas(event=None):
    global shown

    query = search_entry.get().strip()

    if query:
        names = df["pl_name"].astype(str).str.contains(
            query,
            case=False,
            regex=False,
            na=False
        )

        if "hostname" in df.columns:
            stars = df["hostname"].astype(str).str.contains(
                query,
                case=False,
                regex=False,
                na=False
            )
        else:
            stars = pd.Series(
                False,
                index=df.index
            )

        filtered = df[names | stars]
    else:
        filtered = df

    shown = filtered.dropna(
        subset=["pl_bmasse", "pl_dens"]
    )

    shown = shown[
        (shown["pl_bmasse"] > 0) &
        (shown["pl_bmasse"] <= 100) &
        (shown["pl_dens"] > 0) &
        (shown["pl_dens"] <= 20)
    ].reset_index(drop=True)

    planet_list.delete(0, tk.END)

    for name in filtered["pl_name"].head(1000):
        planet_list.insert(tk.END, str(name))

    ax_atlas.clear()
    ax_atlas.set_facecolor(ENTRY)

    ax_atlas.scatter(
        shown["pl_bmasse"],
        shown["pl_dens"],
        s=16,
        color="#5cbbef",
        alpha=0.65,
        picker=5,
        label="NASA"
    )

    ax_atlas.scatter(
        [1],
        [5.51],
        color="#54e3ad",
        marker="*",
        s=140,
        label="Земля"
    )

    ax_atlas.set_xlabel("Масса Земли")
    ax_atlas.set_ylabel("Плотность")
    ax_atlas.set_title(
        f"NASA ATLAS — {len(shown)} точек"
    )

    ax_atlas.grid(alpha=0.2)
    ax_atlas.legend()
    mission_plot_style(ax_atlas, fig_atlas)

    fig_atlas.tight_layout()
    canvas_atlas.draw_idle()


def atlas_click(event):
    if not event.ind:
        return

    if event.artist != ax_atlas.collections[0]:
        return

    index = int(event.ind[0])
    name = shown.iloc[index]["pl_name"]

    open_planet(name)


def open_selected(event=None):
    selection = planet_list.curselection()

    if selection:
        name = planet_list.get(selection[0])
        open_planet(name)


search_entry.bind("<KeyRelease>", update_atlas)

planet_list.bind(
    "<Double-Button-1>",
    open_selected
)

canvas_atlas.mpl_connect(
    "pick_event",
    atlas_click
)

make_button(
    list_panel,
    "ОТКРЫТЬ ДОСЬЕ",
    open_selected
).pack(fill="x", padx=12, pady=12)

update_atlas()


# ============================================================
# ЗВЁЗДНАЯ КАРТА — NASA MISSION CONTROL
# 2D-проекция RA/Dec (не физические расстояния между звёздами).
# ============================================================

star_map_tab = tk.Frame(notebook, bg=CARD)
notebook.add(star_map_tab, text="  ✦ ЗВЁЗДНАЯ КАРТА  ")

# Координаты берём только из NASA CSV, никаких случайных позиций.
for coord in ("ra", "dec"):
    if coord not in df.columns:
        df[coord] = np.nan
    df[coord] = pd.to_numeric(df[coord], errors="coerce")

star_catalog = df.dropna(subset=["ra", "dec"]).copy()
star_catalog = star_catalog[
    star_catalog["ra"].between(0, 360) &
    star_catalog["dec"].between(-90, 90)
].reset_index(drop=True)


# Быстрый кэш координат: pandas не запускается при каждом кадре.
STAR_ROWS = []
for _r in star_catalog.itertuples(index=False):
    _radius = getattr(_r, "pl_rade", float("nan"))
    _color = "#f2bd6e" if pd.notna(_radius) and _radius >= 2 else "#76c5ff"
    if pd.notna(_radius) and _radius <= 1.6:
        _color = "#62e0c2"
    STAR_ROWS.append((float(_r.ra), float(_r.dec), str(_r.pl_name),
                      str(getattr(_r, "hostname", "")), _color))


def make_star_map_view(parent):
    """LOD + viewport culling: only visible objects, limited by screen density."""
    outer = tk.Frame(parent, bg=BG)
    tools = tk.Frame(outer, bg=HEADER)
    tools.pack(fill="x")
    tk.Label(tools, text="  ✦ EXOPLANET SKY MAP  /  RA–DEC",
             bg=HEADER, fg="#c6e7ff",
             font=("Segoe UI", 10, "bold")).pack(side="left", pady=9)
    search_var = tk.StringVar()
    search = tk.Entry(tools, textvariable=search_var, bg=ENTRY,
                      fg=TEXT, insertbackground=TEXT, relief="flat",
                      font=("Segoe UI", 10), width=24)
    search.pack(side="right", padx=12, ipady=5)
    tk.Label(tools, text="Поиск:", bg=HEADER, fg=MUTED).pack(side="right")
    detail_button=make_button(tools,"◉ ПОДРОБНЕЕ / 3D",
                              lambda: open_3d_projection(state["selected"]) if state["selected"] else None)
    detail_button.pack(side="right",padx=6)
    detail_button.configure(state="disabled")
    info = tk.Label(outer, bg=BG, fg="#86a9c6",
                    font=("Segoe UI", 9), anchor="w")
    info.pack(side="bottom", fill="x", padx=10, pady=4)
    sky = tk.Canvas(outer, bg="#091426", highlightthickness=0, cursor="crosshair")
    sky.pack(fill="both", expand=True)

    state = {"zoom": 1.0, "ox": 0.0, "oy": 0.0, "drag": None,
             "points": [], "job": None, "suspended": False, "moved": False, "selected": None}
    # Precomputed sky coordinate bins. Avoid scanning entire NASA catalogue
    # for every viewport update; nearby bins are inspected only as needed.
    # Fixed, deterministic catalogue priority. Panning must never reshuffle
    # the visible subset: choose LOD from the whole catalogue, not viewport.
    import zlib
    ranked = sorted(STAR_ROWS, key=lambda r: (
        zlib.crc32(f"{r[2]}|{r[0]:.8f}|{r[1]:.8f}".encode("utf-8")),
        r[2], r[0], r[1]))
    priority = {id(row): rank for rank, row in enumerate(ranked)}
    spatial = {}
    for row in STAR_ROWS:
        key = (int(row[0] // 5), int((row[1] + 90) // 5))
        spatial.setdefault(key, []).append(row)

    def redraw():
        state["job"] = None
        if state["suspended"] or state["drag"] is not None:
            return
        w, h = sky.winfo_width(), sky.winfo_height()
        if w < 10 or h < 10:
            return
        z = state["zoom"]
        ox, oy = state["ox"], state["oy"]
        sky.delete("all")
        def pos(ra, dec):
            return (w / 2 + (ra - 180) / 360 * w * z + ox,
                    h / 2 - dec / 180 * h * z + oy)

        # Draw only grid lines actually visible in this viewport.
        for ra in range(0, 361, 30):
            x, _ = pos(ra, 0)
            if -20 <= x <= w + 20:
                sky.create_line(x, 0, x, h, fill="#1b304a", tags="grid")
                sky.create_text(x + 3, 9, text=f"{ra}°",
                                fill="#416785", anchor="nw", tags="grid")
        for dec in range(-90, 91, 30):
            _, y = pos(180, dec)
            if -20 <= y <= h + 20:
                sky.create_line(0, y, w, y, fill="#1b304a", tags="grid")

        query = search_var.get().strip().casefold()
        # Inverse projection: find RA/Dec bounds of visible rectangle.
        def inverse(x, y):
            return (180 + (x - w / 2 - ox) * 360 / (w * z),
                    (h / 2 + oy - y) * 180 / (h * z))
        ra0, dec_hi = inverse(0, 0)
        ra1, dec_lo = inverse(w, h)
        ra0, ra1 = max(0, ra0), min(360, ra1)
        dec_lo, dec_hi = max(-90, dec_lo), min(90, dec_hi)
        visible = []
        if ra0 <= ra1 and dec_lo <= dec_hi:
            for bx in range(int(ra0 // 5), int(ra1 // 5) + 1):
                for by in range(int((dec_lo + 90) // 5),
                                int((dec_hi + 90) // 5) + 1):
                    for row in spatial.get((bx, by), ()):
                        ra, dec, name, host, color = row
                        if ra0 <= ra <= ra1 and dec_lo <= dec <= dec_hi:
                            if not query or query in name.casefold() or query in host.casefold():
                                visible.append(row)

        # Stable LOD: the selected catalogue objects depend ONLY on zoom,
        # never on which other objects happen to be inside the viewport.
        # Moving the map therefore cannot make dots exchange places.
        limit = min(len(STAR_ROWS), int(500 * z ** 0.65))
        if not query:
            visible = [row for row in visible if priority[id(row)] < limit]
        # Search always checks the full catalogue; cap only extreme matches.
        elif len(visible) > 1500:
            visible = sorted(visible, key=lambda r: priority[id(r)])[:1500]

        points = []
        radius = 3.5 if query else (2.0 if z < 3 else 2.6)
        for ra, dec, name, host, color in visible:
            x, y = pos(ra, dec)
            sky.create_oval(x-radius, y-radius, x+radius, y+radius,
                            fill=color, outline="", tags="star")
            points.append((x, y, name))
        state["points"] = points
        info.configure(text=f"NASA: {len(STAR_ROWS)} объектов  |  "
                       f"На экране: {len(points)}  |  Масштаб: {z:.1f}×  |  "
                       "Колесо — масштаб · ЛКМ — перемещение · клик — досье")
        if not STAR_ROWS:
            sky.create_text(w/2, h/2,
                text="В world.csv нет координат ra/dec.\nДобавь их из NASA Exoplanet Archive.",
                fill="#d7e9fa", justify="center")

    def request_redraw(*_):
        if state["suspended"]:
            return
        if state["job"] is not None:
            outer.after_cancel(state["job"])
        state["job"] = outer.after(75, redraw)

    def on_press(e):
        state["drag"] = (e.x, e.y)
        state["moved"] = False

    def on_motion(e):
        if state["drag"] is None:
            return
        px, py = state["drag"]
        dx, dy = e.x - px, e.y - py
        if dx == 0 and dy == 0:
            return
        state["drag"] = (e.x, e.y)
        state["moved"] = True
        state["ox"] += dx
        state["oy"] += dy
        sky.move("all", dx, dy)
        # Do not rebuild the points list for every mouse event.
        # Hit testing is refreshed after mouse release.

    def on_release(e):
        if state["drag"] is None:
            return
        state["drag"] = None
        if state["moved"]:
            request_redraw()
            return
        closest = min(state["points"],
                      key=lambda p: (p[0]-e.x)**2 + (p[1]-e.y)**2,
                      default=None)
        if closest and (closest[0]-e.x)**2 + (closest[1]-e.y)**2 < 110:
            state["selected"]=closest[2]
            detail_button.configure(state="normal")
            open_planet(closest[2])

    def wheel(e):
        old = state["zoom"]
        new = max(1.0, min(32.0, old * (1.22 if e.delta > 0 else 1/1.22)))
        if new == old:
            return
        w, h = sky.winfo_width(), sky.winfo_height()
        factor = new / old
        # Keep the sky position under the cursor stationary.
        state["ox"] = e.x-w/2 - (e.x-w/2-state["ox"])*factor
        state["oy"] = e.y-h/2 - (e.y-h/2-state["oy"])*factor
        state["zoom"] = new
        # Cheap visual preview, then one debounced full LOD update.
        sky.scale("star", e.x, e.y, factor, factor)
        sky.scale("grid", e.x, e.y, factor, factor)
        request_redraw()

    def suspend():
        state["suspended"] = True
        if state["job"] is not None:
            outer.after_cancel(state["job"])
            state["job"] = None
        sky.delete("all")
        state["points"] = []

    def refresh():
        state["suspended"] = False
        request_redraw()

    outer.suspend_map = suspend
    outer.refresh_map = refresh
    sky.bind("<Configure>", request_redraw)
    sky.bind("<ButtonPress-1>", on_press)
    sky.bind("<B1-Motion>", on_motion)
    sky.bind("<ButtonRelease-1>", on_release)
    sky.bind("<MouseWheel>", wheel)
    search_var.trace_add("write", request_redraw)
    request_redraw()
    return outer


star_map_view = make_star_map_view(star_map_tab)
star_map_view.pack(fill="both", expand=True)


def float_star_map(tab, x=80, y=80):
    if str(tab) in floating_tabs:
        floating_tabs[str(tab)]["panel"].lift()
        return
    star_map_view.suspend_map()
    notebook.forget(tab)
    root.update_idletasks()
    w = min(850, max(400, root.winfo_width()-60))
    h = min(570, max(300, root.winfo_height()-110))
    x = max(0, min(x, root.winfo_width()-w))
    y = max(45, min(y+45, root.winfo_height()-h))
    panel = tk.Frame(root, bg=CARD, highlightbackground=BLUE,
                     highlightthickness=2)
    panel.place(x=x, y=y, width=w, height=h)
    panel.lift()
    header = tk.Frame(panel, bg=HEADER, height=36, cursor="fleur")
    header.pack(fill="x")
    header.pack_propagate(False)
    label = tk.Label(header, text="  ⠿  ✦ ЗВЁЗДНАЯ КАРТА",
                     bg=HEADER, fg=TEXT, cursor="fleur")
    label.pack(side="left", fill="y")
    tk.Button(header, text="↩ ВО ВКЛАДКИ", bg=BLUE, fg="white",
              relief="flat", command=lambda: dock_tab(tab)).pack(
                  side="right", padx=5, pady=3)
    view = make_star_map_view(panel)
    view.pack(fill="both", expand=True)
    grip = tk.Label(panel, text="◢", bg=BLUE, fg="white",
                    cursor="bottom_right_corner", font=("Segoe UI", 13))
    grip.place(relx=1, rely=1, anchor="se", width=26, height=26)
    floating_tabs[str(tab)] = {"kind": "star_map", "panel": panel}
    move = {}
    def start_move(e):
        panel.lift()
        move.update(mx=e.x_root, my=e.y_root,
                    px=panel.winfo_x(), py=panel.winfo_y())
    def do_move(e):
        if "mx" not in move:
            return
        nx = move["px"] + e.x_root-move["mx"]
        ny = move["py"] + e.y_root-move["my"]
        panel.place_configure(x=max(0,min(nx,root.winfo_width()-100)),
                              y=max(38,min(ny,root.winfo_height()-45)))
    for widget in (header, label):
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)
    resize = {"active":False, "job":None, "pending":None}
    def apply():
        resize["job"] = None
        if resize["active"] and resize["pending"]:
            ww, hh = resize["pending"]
            panel.place_configure(width=ww, height=hh)
            resize["pending"] = None
    def start(e):
        panel.lift()
        resize.update(active=True, mx=e.x_root, my=e.y_root,
                      w=panel.winfo_width(), h=panel.winfo_height())
    def motion(e):
        if not resize["active"]:
            return
        ww = max(360, resize["w"]+e.x_root-resize["mx"])
        hh = max(250, resize["h"]+e.y_root-resize["my"])
        ww = min(ww,max(360,root.winfo_width()-panel.winfo_x()))
        hh = min(hh,max(250,root.winfo_height()-panel.winfo_y()))
        resize["pending"] = (int(ww),int(hh))
        if resize["job"] is None:
            resize["job"] = panel.after(16, apply)
    def stop(e):
        motion(e)
        resize["active"] = False
        if resize["job"] is not None:
            panel.after_cancel(resize["job"])
            resize["job"] = None
        if resize["pending"]:
            panel.place_configure(width=resize["pending"][0],
                                  height=resize["pending"][1])
            resize["pending"] = None
    grip.bind("<ButtonPress-1>", start)
    grip.bind("<B1-Motion>", motion)
    grip.bind("<ButtonRelease-1>", stop)

make_button(star_map_tab, "▣ ОТЦЕПИТЬ КАРТУ",
            lambda: float_tab(star_map_tab)).pack(side="bottom", pady=6)


# ============================================================
# SAVED NOTES LIBRARY
# ============================================================

library_tab = tk.Frame(notebook, bg=CARD)

notebook.add(
    library_tab,
    text="  📚 МОИ ЗАМЕТКИ  "
)

make_label(
    library_tab,
    "БИБЛИОТЕКА ИССЛЕДОВАТЕЛЯ",
    18
).pack(anchor="w", padx=20, pady=20)

library_list = tk.Listbox(
    library_tab,
    bg=ENTRY,
    fg=TEXT,
    selectbackground=BLUE,
    relief="flat",
    font=("Segoe UI", 12)
)

library_list.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)

library_ids = []


def refresh_library():
    global library_ids

    library_list.delete(0, tk.END)

    library_ids = list(notes.keys())

    for note_id in library_ids:
        title = notes[note_id].get(
            "title",
            "Без названия"
        )

        library_list.insert(tk.END, title)


def open_saved_note(event=None):
    selected = library_list.curselection()

    if not selected:
        return

    note_id = library_ids[selected[0]]
    data = notes[note_id]

    create_note(
        note_id=note_id,
        title=data.get("title", "Без названия"),
        content=data.get("text", "")
    )


def show_library(event=None):
    if notebook.select() == str(library_tab):
        refresh_library()


library_list.bind(
    "<Double-Button-1>",
    open_saved_note
)

make_button(
    library_tab,
    "ОТКРЫТЬ ЗАМЕТКУ",
    open_saved_note
).pack(pady=12)

notebook.bind(
    "<<NotebookTabChanged>>",
    show_library
)

refresh_library()


# ============================================================
# AUTOSAVE ON EXIT
# ============================================================

def on_close():
    for note_id in list(note_tabs.keys()):
        save_note(note_id, quiet=True)

    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)


# ============================================================
# START
# ============================================================

notebook.select(ai_tab)
root.mainloop()

import tkinter as tk
from tkinter import ttk
from typing import Dict
from models.cards import SUSPECTS, WEAPONS, ROOMS

STATE_CYCLE = ["", "✓", "✗", "?"]


class ClueSheet(ttk.LabelFrame):
    def __init__(self, master, players, *args, **kwargs):
        super().__init__(master, text="Clue Sheet", *args, **kwargs)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.cells: Dict[str, tk.Label] = {}

        ttk.Label(container, text="", font=("Arial", 12, "bold")).grid(
            row=0, column=0, sticky="nsew"
        )
        for idx, p in enumerate(players, start=1):
            ttk.Label(container, text=p.name, font=("Arial", 10, "bold")).grid(
                row=0, column=idx, padx=4, pady=4, sticky="nsew"
            )
            container.grid_columnconfigure(idx, weight=1, uniform="playercols")

        row = 1
        row = self._add_section(container, "Suspects", SUSPECTS, row)
        row = self._add_section(container, "Weapons", WEAPONS, row)
        self._add_section(container, "Rooms", ROOMS, row)

    def _add_section(self, parent, title: str, items, start_row: int) -> int:
        """Add a section title and its rows; return next available row index."""
        ttk.Label(parent, text=title, font=("TkDefaultFont", 10, "bold")).grid(
            row=start_row, column=0, sticky="w"
        )
        start_row += 1
        for name in items:
            self._add_row(parent, name, start_row)
            start_row += 1
        return start_row

    def _add_row(self, parent, name: str, row: int):
        ttk.Label(parent, text=name).grid(
            row=row, column=0, sticky="w", padx=(0, 8))
        for col in range(1, 4):
            key = f"{name}:{col}"
            lbl = tk.Label(parent, text="", relief="ridge",
                           width=3, bg="white")
            lbl.grid(row=row, column=col, padx=2, pady=1, sticky="nsew")
            lbl.bind("<Button-1>", lambda e, k=key: self._cycle(k))
            self.cells[key] = lbl

    def _cycle(self, key: str):
        lbl = self.cells[key]
        cur = lbl.cget("text")
        nxt = STATE_CYCLE[(STATE_CYCLE.index(cur) + 1) % len(STATE_CYCLE)]
        lbl.config(text=nxt)

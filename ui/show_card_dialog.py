import tkinter as tk
from tkinter import ttk
from typing import Optional, List
from models.cards import Card


class ShowCardDialog(tk.Toplevel):
    def __init__(self, master, cards: List[Card]):
        super().__init__(master)
        self.title("Choose a card to show")
        self.result: Optional[Card] = None
        ttk.Label(self, text="Select which card to show:").pack(
            padx=12, pady=(12, 6))

        self.var = tk.StringVar(value=cards[0].name)
        for c in cards:
            ttk.Radiobutton(
                self,
                text=f"{c.type}: {c.name}",
                value=c.name,
                variable=self.var
            ).pack(anchor="w", padx=12, pady=2)

        btns = ttk.Frame(self)
        btns.pack(pady=12)
        ttk.Button(btns, text="OK", command=self._on_ok).pack(
            side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self._on_cancel).pack(
            side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.transient(master)
        self.grab_set()
        self.wait_window(self)

    def _on_ok(self):
        self.result = self.var.get()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

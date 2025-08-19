import tkinter as tk
from tkinter import ttk
from typing import List
from models.cards import Card


class HandView(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Your hand")
        self.listbox = tk.Listbox(self, height=8)
        self.listbox.pack(fill="x", padx=8, pady=8)

    def update_hand(self, cards: List[Card]):
        self.listbox.delete(0, "end")
        for c in sorted(cards, key=lambda x: (x.type, x.name)):
            self.listbox.insert("end", f"{c.type}: {c.name}")

import tkinter as tk
from tkinter import ttk
from typing import List


class LogView(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Game log")
        self.text = tk.Text(self, height=12, state="disabled", wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)

    def set_lines(self, lines: List[str]):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for line in lines[-300:]:
            self.text.insert("end", line + "\n")
        self.text.configure(state="disabled")
        self.text.see("end")

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from models.cards import Card, category_cards


class Controls(ttk.LabelFrame):
    def __init__(
        self,
        master,
        on_suggest: Callable[[Card, Card, Card], None],
        on_accuse: Callable[[Card, Card, Card], None],
        on_end_turn: Callable[[], None],
    ):
        super().__init__(master, text="Turn controls")
        self.on_suggest = on_suggest
        self.on_accuse = on_accuse
        self.on_end_turn = on_end_turn

        self.turn_label = ttk.Label(self, text="Current: ")
        self.turn_label.pack(fill="x", padx=8, pady=(8, 4))

        form = ttk.Frame(self)
        form.pack(fill="x", padx=8, pady=4)

        # Dropdowns
        self.suspect_var = tk.StringVar()
        self.weapon_var = tk.StringVar()
        self.room_var = tk.StringVar()

        self.suspect_cb = self._make_combo(form, "Suspect", self.suspect_var, [
                                           c.name for c in category_cards("Suspect")])
        self.weapon_cb = self._make_combo(form, "Weapon", self.weapon_var, [
                                          c.name for c in category_cards("Weapon")])
        self.room_cb = self._make_combo(form, "Room", self.room_var, [
                                        c.name for c in category_cards("Room")])

        # Buttons
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(4, 8))

        self.suggest_btn = ttk.Button(
            btns, text="Suggest", command=self._suggest)
        self.suggest_btn.pack(side="left", padx=(0, 6))
        self.accuse_btn = ttk.Button(btns, text="Accuse", command=self._accuse)
        self.accuse_btn.pack(side="left", padx=(0, 6))
        self.end_btn = ttk.Button(
            btns, text="End turn", command=self.on_end_turn)
        self.end_btn.pack(side="left", padx=(0, 6))

    def _make_combo(self, parent, label, var, values):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=8).pack(side="left")
        cb = ttk.Combobox(row, textvariable=var,
                          values=values, state="readonly")
        cb.pack(side="left", fill="x", expand=True)
        if values:
            var.set(values[0])
        return cb

    def update_options(self):
        # no-op placeholder; could filter options based on knowledge
        pass

    def set_turn_owner(self, name: str, is_human: bool):
        self.turn_label.config(
            text=f"Current: {name} {'(You)' if is_human else ''}")
        state = "normal" if is_human else "disabled"
        for w in (self.suspect_cb, self.weapon_cb, self.room_cb, self.suggest_btn, self.accuse_btn, self.end_btn):
            w.configure(state=state)

    def set_suggest_enabled(self, enabled: bool):
        self.suggest_btn.configure(state="normal" if enabled else "disabled")

    def _get_selected(self):
        def pick(cat):
            name = {
                "Suspect": self.suspect_var.get(),
                "Weapon": self.weapon_var.get(),
                "Room": self.room_var.get(),
            }[cat]
            return next(c for c in category_cards(cat) if c.name == name)
        return pick("Suspect"), pick("Weapon"), pick("Room")

    def _suggest(self):
        s, w, r = self._get_selected()
        self.on_suggest(s, w, r)

    def _accuse(self):
        s, w, r = self._get_selected()
        self.on_accuse(s, w, r)

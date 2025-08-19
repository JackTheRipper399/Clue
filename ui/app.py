import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from models.cards import Card, category_cards
from logic.game_engine import GameEngine
from ui.hand_view import HandView
from ui.clue_sheet import ClueSheet
from ui.log_view import LogView
from ui.controls import Controls


class ClueApp(tk.Frame):
    def __init__(self, master: tk.Tk, engine: GameEngine):
        super().__init__(master)
        self.engine = engine
        self.engine.set_ui(self)
        self._build_layout()
        self._refresh_all()
        self._maybe_run_ai_turn()

    def _build_layout(self):
        # Left: hand + controls
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)

        self.hand_view = HandView(left)
        self.hand_view.pack(fill="x", pady=(0, 8))

        self.controls = Controls(left, on_suggest=self._on_suggest,
                                 on_accuse=self._on_accuse, on_end_turn=self._on_end_turn)
        self.controls.pack(fill="x")

        # Right: clue sheet + log
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.sheet = ClueSheet(right, players=self.engine.players)
        self.sheet.pack(fill="both", expand=True, pady=(0, 8))

        self.log_view = LogView(right)
        self.log_view.pack(fill="both", expand=True)

    def _refresh_all(self):
        human = next(p for p in self.engine.players if p.is_human)
        self.hand_view.update_hand(human.hand)
        self.controls.update_options()
        self._refresh_log()
        self._update_turn_state()

    def _refresh_log(self):
        self.log_view.set_lines([e.text for e in self.engine.logs])

    def _update_turn_state(self):
        cur = self.engine.current_player
        self.controls.set_turn_owner(cur.name, is_human=cur.is_human)
        # allow suggest only if it's human's turn and suggestion not yet used
        if cur.is_human and not self.engine.game_over:
            self.controls.set_suggest_enabled(
                not self.engine.suggested_this_turn)
        else:
            self.controls.set_suggest_enabled(False)

    def _on_suggest(self, suspect: Card, weapon: Card, room: Card):
        cur = self.engine.current_player
        if not cur.is_human:
            return
        result = self.engine.handle_suggestion(cur, suspect, weapon, room)
        if result["shower"]:
            if result["card"] is not None:
                messagebox.showinfo(
                    "Card shown", f"{result['shower']} showed you: {result['card'].name}")
            else:
                messagebox.showinfo(
                    "Card shown", f"{result['shower']} showed a card.")
        else:
            messagebox.showinfo(
                "No refute", "No one could refute your suggestion.")
        self._refresh_all()
        # ensure Suggest stays disabled after use
        self.controls.set_suggest_enabled(False)

    def _on_accuse(self, suspect: Card, weapon: Card, room: Card):
        cur = self.engine.current_player
        if not cur.is_human:
            return
        if self.engine.check_accusation(cur, suspect, weapon, room):
            messagebox.showinfo(
                "You win!", "Your accusation is correct. Game over.")
            self._refresh_all()
        else:
            messagebox.showwarning(
                "Incorrect", "Your accusation is incorrect. You are out.")
            # immediately pass turn to next active player and continue
            self.engine.next_turn()
            self._refresh_all()
            self._maybe_run_ai_turn()

    def _on_end_turn(self):
        self.engine.next_turn()
        self._refresh_all()
        self._maybe_run_ai_turn()

    def _maybe_run_ai_turn(self):
        if self.engine.game_over:
            return
        cur = self.engine.current_player
        if cur.is_human:
            return
        self.after(500, self._run_ai_turn)

    def _run_ai_turn(self):
        if self.engine.game_over:
            return
        cur = self.engine.current_player
        if not cur.is_human:
            from models.player import AIPlayer
            ai: AIPlayer = cur  # type: ignore
            acc = ai.decide_accusation()
            if acc:
                s, w, r = acc
                self.engine.log(f"{ai.name} declares an accusation!")
                correct = self.engine.check_accusation(ai, s, w, r)
                self._refresh_all()
                if correct:
                    messagebox.showinfo(
                        "AI wins", f"{ai.name} made a correct accusation!")
                    return
                else:
                    # AI is eliminated; advance to next active player
                    self.engine.next_turn()
                    self._refresh_all()
                    self._maybe_run_ai_turn()
                    return

            # Suggest (only if still active and no accusation was made)
            if not self.engine.game_over and ai.is_active:
                s, w, r = ai.decide_suggestion()
                _ = self.engine.handle_suggestion(ai, s, w, r)
                self._refresh_all()
                self.engine.next_turn()
                self._refresh_all()
                self._maybe_run_ai_turn()

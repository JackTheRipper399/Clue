import random
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from models.cards import Card, all_cards, category_cards
from models.player import Player, AIPlayer
from logic.knowledge_base import ENVELOPE
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.app import ClueApp  # type hint only


@dataclass
class LogEntry:
    text: str


@dataclass
class GameEngine:
    human_name: str = "You"
    ai_count: int = 2
    players: List[Player] = field(default_factory=list)
    solution: Tuple[Card, Card, Card] = None  # type: ignore
    deck: List[Card] = field(default_factory=list)
    turn_index: int = 0
    logs: List[LogEntry] = field(default_factory=list)

    # NEW
    suggested_this_turn: bool = False
    game_over: bool = False
    winner: Optional[str] = None

    def __post_init__(self):
        self._setup_game()

    def _setup_game(self) -> None:
        # Create players
        self.players = [Player(self.human_name, True)] + \
            [AIPlayer(f"AI {i+1}") for i in range(self.ai_count)]
        for p in self.players:
            p.is_active = True  # ensure everyone starts active

        # Build solution and deal
        suspects = category_cards("Suspect")
        weapons = category_cards("Weapon")
        rooms = category_cards("Room")
        sol = (random.choice(suspects), random.choice(
            weapons), random.choice(rooms))
        self.solution = sol

        deck = [c for c in all_cards() if c not in sol]
        random.shuffle(deck)
        self.deck = deck

        # Deal cards round-robin
        i = 0
        while deck:
            self.players[i % len(self.players)].receive_cards([deck.pop()])
            i += 1

        # Initialize AI knowledge bases
        names = [p.name for p in self.players]
        for p in self.players:
            if isinstance(p, AIPlayer):
                p.on_dealt(names, all_cards())

        self.log(f"Game started with players: {', '.join(names)}.")
        self._ensure_turn_on_active()
        self.suggested_this_turn = False

    def _active_players(self) -> List[Player]:
        return [p for p in self.players if getattr(p, "is_active", True)]

    def set_ui(self, ui: "ClueApp"):
        """Attach the UI to allow human interaction during events like showing a card."""
        self.ui = ui

    def _maybe_end_if_single_remaining(self) -> None:
        actives = self._active_players()
        if len(actives) == 1 and not self.game_over:
            self.game_over = True
            self.winner = actives[0].name
            self.log(f"{self.winner} wins by being the last active player.")

    def _ensure_turn_on_active(self) -> None:
        # Move turn_index to an active player if current is inactive
        if not self.players:
            return
        for _ in range(len(self.players)):
            if self.players[self.turn_index].is_active:
                return
            self.turn_index = (self.turn_index + 1) % len(self.players)

    @property
    def current_player(self) -> Player:
        self._ensure_turn_on_active()
        return self.players[self.turn_index % len(self.players)]

    def next_turn(self) -> None:
        if self.game_over:
            return
        # advance to next active player
        for _ in range(len(self.players)):
            self.turn_index = (self.turn_index + 1) % len(self.players)
            if self.players[self.turn_index].is_active:
                break
        self.suggested_this_turn = False
        self._maybe_end_if_single_remaining()

    def log(self, msg: str) -> None:
        self.logs.append(LogEntry(msg))
        # Trim to avoid runaway growth
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

    def player_order_after(self, player: Player) -> List[Player]:
        idx = self.players.index(player)
        order = []
        for k in range(1, len(self.players)):
            order.append(self.players[(idx + k) % len(self.players)])
        return order

    def handle_suggestion(self, suggester: Player, suspect: Card, weapon: Card, room: Card) -> Dict[str, Optional[Card]]:
        result: Dict[str, Optional[Card]] = {"shower": None, "card": None}

        # block multiple suggestions in the same turn
        if self.game_over:
            self.log("Game is over. No further suggestions.")
            return result
        if suggester != self.current_player:
            self.log(f"It is not {suggester.name}'s turn.")
            return result
        if self.suggested_this_turn:
            self.log(f"{suggester.name} already made a suggestion this turn.")
            return result

        suggested = [suspect, weapon, room]
        self.log(
            f"{suggester.name} suggests: {suspect.name} with the {weapon.name} in the {room.name}.")

        passes_before_refute: List[str] = []
        result: Dict[str, Optional[Card]] = {"shower": None, "card": None}

        for responder in self.player_order_after(suggester):
            if responder.has_any(suggested):
                if responder.is_human:
                    # Human chooses a card to show
                    from ui.show_card_dialog import ShowCardDialog
                    dialog = ShowCardDialog(self.ui.winfo_toplevel(), [
                                            c for c in suggested if c in responder.hand])
                    chosen_name = dialog.result
                    shown = None
                    if chosen_name:
                        shown = next(
                            c for c in responder.hand if c.name == chosen_name)
                else:
                    shown = responder.choose_card_to_show(
                        suggested, self.current_player.name)
                if shown is None:
                    # Should not happen given has_any
                    passes_before_refute.append(responder.name)
                    continue
                # Notify knowledge bases
                if isinstance(suggester, AIPlayer):
                    suggester.note_refute_seen(responder.name, shown)
                    for passer in passes_before_refute:
                        suggester.note_pass(passer, suggested)
                else:
                    # Human saw the card; AI only knows someone refuted
                    for p in self.players:
                        if isinstance(p, AIPlayer) and p.name != responder.name:
                            p.note_has_one_of(responder.name, suggested)
                        if isinstance(p, AIPlayer):
                            for passer in passes_before_refute:
                                p.note_pass(passer, suggested)
                self.log(f"{responder.name} shows a card to {suggester.name}.")
                result["shower"] = responder.name
                result["card"] = shown if suggester.is_human else None
                self.suggested_this_turn = True
                return result
            else:
                passes_before_refute.append(responder.name)

        # No one could refute; update KBs
        self.log("No one could refute the suggestion.")
        if isinstance(suggester, AIPlayer):
            for passer in passes_before_refute:
                suggester.note_pass(passer, suggested)
            # If no one refuted and suggester doesn't own these, they may infer envelope candidates
            # Handled by generic propagation when future notes appear
        else:
            for p in self.players:
                if isinstance(p, AIPlayer):
                    for passer in passes_before_refute:
                        p.note_pass(passer, suggested)
        self.suggested_this_turn = True
        return result

    def check_accusation(self, accuser: Player, suspect: Card, weapon: Card, room: Card) -> bool:
        if self.game_over:
            return False
        correct = (suspect, weapon, room) == self.solution
        if correct:
            self.log(
                f"{accuser.name} accuses correctly! {suspect.name} with the {weapon.name} in the {room.name}.")
            self.game_over = True
            self.winner = accuser.name
        else:
            self.log(
                f"{accuser.name} accuses incorrectly and is out of the game.")
            accuser.is_active = False
            self._maybe_end_if_single_remaining()
        return correct

    def take_ai_turn(self, ai: AIPlayer):
        """Runs an AI turn: attempt accusation, else make a suggestion."""
        self.debug_probs(ai)  # See their current probability table

        accusation = ai.decide_accusation()
        if accusation:
            s, w, r = accusation
            self.log(
                f"{ai.name} decides to accuse: {s.name} with the {w.name} in the {r.name}")
            self.check_accusation(ai, s, w, r)
            return

        # If no accusation is made
        s, w, r = ai.decide_suggestion()
        self.handle_suggestion(ai, s, w, r)

    def debug_probs(self, ai: AIPlayer):
        """Print the top three envelope candidates per category."""
        from models.cards import category_cards, card_key
        print(f"\n[{ai.name} probability snapshot]")
        for cat in ("Suspect", "Weapon", "Room"):
            items = sorted(
                [(c.name, round(ai.kb.envelope_probs[card_key(c)], 3))
                 for c in category_cards(cat)],
                key=lambda x: x[1],
                reverse=True
            )
            print(f"{cat}: {items[:3]}")

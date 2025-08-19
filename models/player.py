import random
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from models.cards import Card, CardType, category_cards, card_key
from logic.knowledge_base import KnowledgeBase, ENVELOPE


@dataclass
class Player:
    name: str
    is_human: bool
    hand: List[Card] = field(default_factory=list)
    is_active: bool = True

    def receive_cards(self, cards: List[Card]) -> None:
        self.hand.extend(cards)

    def has_any(self, cards: List[Card]) -> bool:
        return any(c in self.hand for c in cards)

    def choose_card_to_show(self, suggested: List[Card], suggester: str) -> Optional[Card]:
        # Only AI uses this; humans use a dialog in the UI.
        matches = [c for c in suggested if c in self.hand]
        if not matches:
            return None

        # 1. Prefer to show a card already known to the suggester
        known_cards = [c for c in matches if getattr(
            self, "kb", None) and self.kb.is_known_to_player(suggester, c)]
        if known_cards:
            return random.choice(known_cards)

        # 2. If none known, pick one that’s already been refuted before
        refuted_cards = [c for c in matches if getattr(
            self, "kb", None) and self.kb.has_been_refuted_before(c)]
        if refuted_cards:
            return random.choice(refuted_cards)

        # 3. Otherwise, pick at random
        return random.choice(matches)


class AIPlayer(Player):
    def __init__(self, name: str):
        super().__init__(name=name, is_human=False)
        self.kb = KnowledgeBase(self.name)
        self.last_unrefuted_suggestion: Optional[Tuple[str,
                                                       Tuple[Card, Card, Card]]] = None

    def on_dealt(self, players: List[str], all_cards: List[Card]) -> None:
        self.kb.initialize(players, all_cards, self.hand)

    def note_pass(self, passer: str, suggested: List[Card]) -> None:
        self.kb.note_cannot_have_any(passer, suggested)

    def note_refute_seen(self, shower: str, card: Card) -> None:
        self.kb.note_has_card(shower, card)

    def note_refute_happened(self, shower: str, suggested: List[Card]) -> None:
        # We know shower has at least one of suggested, but not which
        self.kb.note_has_one_of(shower, suggested)

    def note_has_one_of(self, player: str, suggested: List[Card]) -> None:
        self.kb.note_has_one_of(player, suggested)

    def note_no_one_refuted(self, suggested: List[Card], suggester: str) -> None:
        """If we're the suggester: mark envelope for any we don't hold."""
        if self.name == suggester:
            for card in suggested:
                if card not in self.hand:
                    self.kb.mark_envelope(card)
        # All AIs remember this event for a possible probe
        self.last_unrefuted_suggestion = (suggester, tuple(suggested))

    def try_infer_envelope_after_no_refute(self, suggester: str, suggested: List[Card]) -> None:
        for card in suggested:
            ck = card_key(card)
            holders = self.kb.matrix[ck]

            if all(holders[p] is False for p in self.kb.players):
                # Certain → mark as envelope
                self.kb.mark_envelope(card)
            else:
                # Soft evidence → nudge probability upward
                if holders[ENVELOPE] is None:
                    bump = 0.15  # tweakable learning rate
                    self.kb.envelope_probs[ck] = min(
                        1.0, self.kb.envelope_probs[ck] + bump)

        # Remember triple for possible probing
        self.last_unrefuted_suggestion = (suggester, tuple(suggested))

    def decide_suggestion(self) -> Tuple[Card, Card, Card]:
        # --- PROBE LOGIC ---
        if self.last_unrefuted_suggestion:
            suggester_name, triple = self.last_unrefuted_suggestion
            if suggester_name in self.kb.players:
                # Only probe if at least one card in triple is still unknown for that player
                if any(self.kb.is_known_to_player(suggester_name, c) is None for c in triple):
                    self.last_unrefuted_suggestion = None  # Use it once
                    return triple

        # If ready to accuse, make that suggestion to confirm; else pick weighted unknowns
        maybe_solution = self.kb.current_solution_guess()
        if maybe_solution:
            return maybe_solution

        # Dynamic exploration → exploitation based on progress
        total_cards = len(self.kb.matrix)
        seen_cards = len(self.kb.refuted_cards)
        progress_ratio = seen_cards / total_cards if total_cards else 0.0
        info_weight = max(0.0, 0.5 * (1.0 - progress_ratio))

        guess: List[Card] = []
        for cat in ("Suspect", "Weapon", "Room"):
            candidates = category_cards(cat)

            def score(card: Card) -> float:
                ck = card_key(card)
                env_prob = self.kb.envelope_probs[ck]
                unknown_holders = sum(
                    1 for p in self.kb.players
                    if self.kb.is_known_to_player(p, card) is None
                )
                info_gain = (unknown_holders / len(self.kb.players)
                             ) if self.kb.players else 0.0
                return env_prob + info_weight * info_gain

            best = max(candidates, key=score)
            guess.append(best)

        return tuple(guess)

    def decide_accusation(self) -> Optional[Tuple[Card, Card, Card]]:
        # 1) Absolute certainty
        confirmed = self.kb.confirmed_solution()
        if confirmed:
            return confirmed

        # 2) Unique candidate per category
        unique_guess = self.kb.current_solution_guess()
        if unique_guess:
            return unique_guess

        # 3) Confidence-based accusation off normalized category probabilities
        def top_two(cat: CardType):
            items = [
                (c, self.kb.envelope_probs[card_key(c)])
                for c in category_cards(cat)
                if self.kb.matrix[card_key(c)][ENVELOPE] is not False
            ]
            items.sort(key=lambda x: x[1], reverse=True)
            top_card, p1 = items[0]
            p2 = items[1][1] if len(items) > 1 else 0.0
            return top_card, p1, p2

        s_card, ps1, ps2 = top_two("Suspect")
        w_card, pw1, pw2 = top_two("Weapon")
        r_card, pr1, pr2 = top_two("Room")

        # Progress: how much envelope space is eliminated
        total_env_slots = sum(len(category_cards(cat))
                              for cat in ("Suspect", "Weapon", "Room"))
        eliminated = sum(
            1 for cat in ("Suspect", "Weapon", "Room") for c in category_cards(cat)
            if self.kb.matrix[card_key(c)][ENVELOPE] is False
        )
        progress = eliminated / total_env_slots if total_env_slots else 0.0

        # Dynamic thresholds: cautious early, assertive late
        per_cat_min = 0.50 + 0.25 * progress       # 0.50 → 0.75
        margin_min = 0.05 + 0.15 * progress        # 0.05 → 0.20
        product_min = 0.20 + 0.30 * progress       # 0.20 → 0.50

        # Bold risk shortcuts
        RISK_ACCUSATION_THRESHOLD = 0.85
        BIG_MARGIN = 0.40

        # Shortcut 1: Very high confidence in each category
        if ps1 >= RISK_ACCUSATION_THRESHOLD and pw1 >= RISK_ACCUSATION_THRESHOLD and pr1 >= RISK_ACCUSATION_THRESHOLD:
            return (s_card, w_card, r_card)

        # Shortcut 2: Huge margin + reasonably high confidence
        if ((ps1 - ps2) >= BIG_MARGIN and ps1 >= 0.75 and
            (pw1 - pw2) >= BIG_MARGIN and pw1 >= 0.75 and
                (pr1 - pr2) >= BIG_MARGIN and pr1 >= 0.75):
            return (s_card, w_card, r_card)

        # Standard dynamic threshold checks
        if not (ps1 >= per_cat_min and pw1 >= per_cat_min and pr1 >= per_cat_min):
            return None
        if not ((ps1 - ps2) >= margin_min and (pw1 - pw2) >= margin_min and (pr1 - pr2) >= margin_min):
            return None

        product_conf = ps1 * pw1 * pr1
        if product_conf < product_min:
            return None

        return (s_card, w_card, r_card)

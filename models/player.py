import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from models.cards import Card, CardType, category_cards
from logic.knowledge_base import KnowledgeBase


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
        matches = [c for c in suggested if c in self.hand]
        if not matches:
            return None

        # 1. Prefer to show a card already known to the suggester
        known_cards = [
            c for c in matches if self.kb.is_known_to_player(suggester, c)]
        if known_cards:
            return random.choice(known_cards)

        # 2. If none known, pick one that’s already been refuted before
        refuted_cards = [
            c for c in matches if self.kb.has_been_refuted_before(c)]
        if refuted_cards:
            return random.choice(refuted_cards)

        # 3. Otherwise, pick at random
        return random.choice(matches)


class AIPlayer(Player):
    def __init__(self, name: str):
        super().__init__(name=name, is_human=False)
        self.kb = KnowledgeBase(self.name)

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

    def decide_suggestion(self) -> Tuple[Card, Card, Card]:
        # If ready to accuse, make that suggestion to confirm; else pick informative unknowns
        maybe_solution = self.kb.current_solution_guess()
        if maybe_solution:
            return maybe_solution

        def pick(cat: CardType) -> Card:
            # Prefer cards that are still possible for ENVELOPE; else any unknown
            unknowns = self.kb.possible_in_envelope(cat)
            if unknowns:
                return random.choice(unknowns)
            # fallback: any card not in our hand and still uncertain
            for c in category_cards(cat):
                if not self.kb.is_card_resolved(c):
                    return c
            return random.choice(category_cards(cat))  # absolute fallback

        return (pick("Suspect"), pick("Weapon"), pick("Room"))

    def decide_accusation(self) -> Optional[Tuple[Card, Card, Card]]:
        return self.kb.confirmed_solution()

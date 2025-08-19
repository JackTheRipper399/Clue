from dataclasses import dataclass
from typing import List, Literal

CardType = Literal["Suspect", "Weapon", "Room"]


@dataclass(frozen=True)
class Card:
    name: str
    type: CardType


SUSPECTS: List[str] = [
    "Miss Scarlet",
    "Colonel Mustard",
    "Mrs. White",
    "Mr. Green",
    "Mrs. Peacock",
    "Professor Plum",
]

WEAPONS: List[str] = [
    "Candlestick",
    "Dagger",
    "Lead Pipe",
    "Revolver",
    "Rope",
    "Wrench",
]

ROOMS: List[str] = [
    "Kitchen",
    "Ballroom",
    "Conservatory",
    "Dining Room",
    "Billiard Room",
    "Library",
    "Lounge",
    "Hall",
    "Study",
]


def all_cards() -> List[Card]:
    return (
        [Card(n, "Suspect") for n in SUSPECTS] +
        [Card(n, "Weapon") for n in WEAPONS] +
        [Card(n, "Room") for n in ROOMS]
    )


def category_cards(cat: CardType) -> List[Card]:
    if cat == "Suspect":
        return [Card(n, "Suspect") for n in SUSPECTS]
    if cat == "Weapon":
        return [Card(n, "Weapon") for n in WEAPONS]
    return [Card(n, "Room") for n in ROOMS]


def card_key(card: Card) -> str:
    return f"{card.type}:{card.name}"

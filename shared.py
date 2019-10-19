#!/usr/bin/env python3

from dataclasses import dataclass
from math import ceil, sqrt
from typing import List, Tuple, Optional


@dataclass
class Planet():
    id: int
    x: int
    y: int
    owner_id: id
    ships: Tuple[int, int, int]
    prodution: Tuple[int, int, int]

    def distance(self, other: 'Planet'):
        xdiff = self.posx - other.posx
        ydiff = self.posy - other.posy
        return int(ceil(sqrt(xdiff * xdiff + ydiff * ydiff)))

    def comp(self, other: 'Planet'):
        return (self.ships[0] - other.ships[0]) + (self.ships[1] - other.ships[1]) + (self.ships[2] - other.ships[2])
        

    @staticmethod
    def load(raw: dict) -> 'Planet':
        return Planet(
            raw['id'],
            raw['x'],
            raw['y'],
            raw["owner_id"],
            raw['ships'],
            raw['production'],
        )


@dataclass
class Fleet():
    id: int
    owner_id: int
    ships: Tuple[int, int, int]
    origin_id: int
    target_id: int
    eta: int

    @staticmethod
    def load(raw: dict) -> 'Fleet':
        return Fleet(
            raw["id"],
            raw["owner_id"],
            raw["ships"],
            raw["origin"],
            raw["target"],
            raw["eta"],
        )


@dataclass
class Player():
    id: int
    itsme: bool
    name: str

    @staticmethod
    def load(raw: dict) -> 'Player':
        return Player(
            raw['id'],
            raw['itsme'],
            raw['name'],
        )


@dataclass
class GameState():
    planets: List[Planet]
    fleets: List[Fleet]
    round: int
    winner: Optional[int]
    player_id: Optional[int]
    players: List[Player]

    @staticmethod
    def load(raw: dict) -> 'GameState':

        return GameState(
            list(map(Planet.load, raw['planets'])),
            list(map(Fleet.load, raw['fleets'])),
            raw['round'],
            raw['winner'],
            raw['player_id'],
            list(map(Player.load, raw['players'])),
        )



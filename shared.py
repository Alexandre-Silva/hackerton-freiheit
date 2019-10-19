#!/usr/bin/env python3

from dataclasses import dataclass, field
from math import ceil, sqrt
from typing import List, Tuple, Optional, Iterable
import pprint
import csv

LOG_CSV_COLUMNS = ['escape', 'harass', 'attack', 'victory']
CSV_FILE = "istsatlog.csv"

@dataclass
class Planet():
    id: int
    x: int
    y: int
    owner_id: id
    ships: Tuple[int, int, int]
    prodution: Tuple[int, int, int]

    def distance(self, other: 'Planet'):
        xdiff = self.x - other.x
        ydiff = self.y - other.y
        return int(ceil(sqrt(xdiff * xdiff + ydiff * ydiff)))

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

    def __hash__(self):
        return hash(self.id)


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


@dataclass
class GameStatePer():
    _dists_tbl: dict = field(default_factory=dict)

    def calculate_dists(self, s: GameState):
        for a in self.planets:
            self._dists_tbl[a] = dict()
            for b in self.planets:
                self._dists_tbl[a][b] = a.distance(b)

        pprint.pprint(self._dists_tbl)

gsp:GameStatePer= GameStatePer()

def neutrals(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id == 0:
            yield p


def make_move(sp: GameStatePer, s: GameState) -> str:

    for p in neutrals(s):
        best_from, best_to = None, None
        # p.

    if True:
        return 'nop'

    else:
        return 'nop'


def log(data):
    try:
        with open(CSV_FILE, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=LOG_CSV_COLUMNS)
            writer.writeheader()
            writer.writerow(data)
    except IOError:
        print("I/O error")


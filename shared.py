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

    def comp(self, other: 'Planet'):
        return (self.ships[0] - other.ships[0]) + (
            self.ships[1] - other.ships[1]) + (self.ships[2] - other.ships[2])

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
    game_over: bool
    player_id: Optional[int]
    players: List[Player]

    @property
    def over(self) -> bool:
        return self.winner is not None or self.game_over

    @staticmethod
    def load(raw: dict) -> 'GameState':

        return GameState(
            list(map(Planet.load, raw['planets'])),
            list(map(Fleet.load, raw['fleets'])),
            raw['round'],
            raw['winner'],
            raw['game_over'],
            raw['player_id'],
            list(map(Player.load, raw['players'])),
        )


@dataclass
class GameStatePer():
    inited: bool = False
    _dists_tbl: dict = field(default_factory=dict)

    def init(self, s: GameState):
        if self.inited:
            return

        self.calculate_dists(s)

    def calculate_dists(self, s: GameState):
        for a in s.planets:
            self._dists_tbl[a] = dict()
            for b in s.planets:
                self._dists_tbl[a][b] = a.distance(b)

    def dist(self, a: int, b: int) -> int:
        return self._dists_tbl[a][b]


def friendly(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id == s.player_id:
            yield p


def neutrals(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id == 0:
            yield p


def incoming_fleets(s: GameState, planet: Planet) -> Iterable[Fleet]:
    for f in s.fleets:
        if f.target_id == planet.id:
            yield f


def move(from_: Planet, to: Planet, shipa: int, shipb: int, shipc: int) -> str:
    return f'send {from_.id} {to.id} {shipa} {shipb} {shipc}'


def strat_capture_neutrals(sp: GameStatePer, s: GameState) -> str:

    best_from, best_to, best_dist = None, None, 0
    for n in neutrals(s):
        for mine in friendly(s):
            dist = sp.dist(mine, n)

            if best_from is not None and best_dist <= dist:
                continue

            # already has incoming friendly fleet
            inc = incoming_fleets(s, n)
            inc = list(filter(lambda f: f.owner_id == s.player_id, inc))
            if len(inc) > 0:
                continue

            best_from, best_to, best_dist = mine, n, dist

    if best_from is not None:
        return move(
            best_from,
            best_to,
            best_from.ships[0],
            best_from.ships[1],
            best_from.ships[2],
        )

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


def simulate_fight(src_planet, target_planet, ships):
    distance = src_planet.distance(target_planet)
    ship_inc = distance * target_planet.production

    attacker = src_planet.ships
    defender = [n + ship_inc for n in target_planet.ships]

    target_result = battle_round(attacker, defender)
    src_result = battle_round(defender, attacker)

    return src_result, target_result

def troops_needed(src_planet, target_planet, ships):
    distance = src_planet.distance(target_planet)
    ship_inc = [distance * p for p in target_planet.production]

    attacker = src_planet.ships
    defender = [n + ship_inc[i] + 1 for i, n in enumerate(target_planet.ships)]

    return defender


def battle_round(attacker, defender):
    # only an asymetric round. this needs to be called twice
    numships = len(attacker)
    defender = defender[::]
    for def_type in range(0, numships):
        for att_type in range(0, numships):
            if def_type == att_type:
                multiplier = 0.1
                absolute = 1
            if (def_type - att_type) % numships == 1:
                multiplier = 0.25
                absolute = 2
            if (def_type - att_type) % numships == numships - 1:
                multiplier = 0.01
                absolute = 1
            defender[def_type] -= max((attacker[att_type] * multiplier),
                                      (attacker[att_type] > 0) * absolute)
        defender[def_type] = max(0, defender[def_type])
    return defender

def battle(s1,s2):
    ships1 = s1[::]
    ships2 = s2[::]
    while sum(ships1) > 0 and sum(ships2) >0:
        new1 = battle_round(ships2,ships1)
        ships2 = battle_round(ships1,ships2)
        ships1 = new1
        #print ships1,ships2

    ships1 = map(int,ships1)
    ships2 = map(int,ships2)
    #print ships1,ships2
    return ships1, ships2


class Agent():
    def __init__(self):
        self.sp = GameStatePer()
        self.s: Optional[GameState] = None

    def tick(self, raw: dict) -> str:
        s = GameState.load(raw)
        self.s = s

        self.sp.init(s)
        sp = self.sp

        if s.over:
            if s.winner == s.player_id:
                print('Victory')
            else:
                print('Defeat')

            return 'nop'

        return strat_capture_neutrals(sp, s)

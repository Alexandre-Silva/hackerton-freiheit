#!/usr/bin/env python3
import os.path

from dataclasses import dataclass, field, fields, asdict
from math import ceil, sqrt
from typing import List, Tuple, Optional, Iterable, Union, Dict, Any, Callable, Set
from typing import List, Tuple, Optional, Iterable, Union
import time
import pprint
import csv


@dataclass
class Stats():
    Nop: int = 0
    CaptureSimple: int = 0
    CaptureMultiStart: int = 0
    CaptureMultiSend2: int = 0
    CaptureMultiCancel: int = 0
    Bailout: int = 0
    Victory: bool = False
    Opponent: str = None


stats = Stats()

CSV_FILE = "istsatlog.csv"

Move = Union['Nop', 'Send']
Ships = Tuple[int, int, int]

PRIO_CAPTURE_MULTI_START = 6
PRIO_CAPTURE_SIMPLE = 5
PRIO_CAPTURE_MULTI_2ND = 4
PRIO_BAILOUT = 1


def ships_add(a: Ships, b: Ships) -> Ships:
    return [x + y for x, y in zip(a, b)]


def ships_sub(a: Ships, b: Ships) -> Ships:
    return [x - y for x, y in zip(a, b)]


def ships_lt(a: Ships, b: Ships) -> Ships:
    return sum(a) < sum(b)


@dataclass
class Planet():
    id: int
    x: int
    y: int
    owner_id: id
    ships: Ships
    production: Ships

    def distance(self, other: 'Planet'):
        xdiff = self.x - other.x
        ydiff = self.y - other.y
        return int(ceil(sqrt(xdiff * xdiff + ydiff * ydiff)))

    def comp(self, other: 'Planet'):
        return (self.ships[0] - other.ships[0]) + (
            self.ships[1] - other.ships[1]) + (self.ships[2] - other.ships[2])

    def ships_in(self, ticks: int) -> Ships:
        '''
        Returns ships that will be in the planet after `ticks`
        '''

        ships_inc = self.ships_produced_in(ticks)

        ships = [0, 0, 0]
        for i in range(3):
            ships[i] = self.ships[i] + ships_inc[i]

        return ships

    def ships_produced_in(self, ticks: int) -> Ships:
        ships_inc = [0, 0, 0]
        for i in range(3):
            ships_inc[i] = ticks * self.production[i]

        return ships_inc

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
    ships: Ships
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

    _planet_dict: Dict[int, Planet] = field(init=False)
    _fleet_dict: Dict[int, Planet] = field(init=False)

    def __post_init__(self):
        self._planet_dict = {p.id: p for p in self.planets}
        self._fleet_dict = {f.id: f for f in self.fleets}

    def planet_get(self, id: int) -> Planet:
        return self._planet_dict[id]

    def fleet_get(self, id: int) -> Fleet:
        return self._fleet_dict[id]

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
    strat_states: Dict[str, Any] = field(init=False)
    reserved_planets: Set[Planet] = field(default_factory=set)

    _dists_tbl: dict = field(default_factory=dict)

    def __post_init__(self):
        self.strat_states = dict()

        cls = StratCaptureMultiPlanetState
        self.strat_states[cls.__name__] = cls(0, 0, 0, 0)

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

    def reserve(self, p: Planet):
        if isinstance(p, Planet):
            id = p.id
        elif isinstance(p, int):
            id = p
        else:
            assert False

        self.reserved_planets.add(id)

    def unreserve(self, p: Union[Planet, int]):
        if isinstance(p, Planet):
            id = p.id
        elif isinstance(p, int):
            id = p
        else:
            assert False

        if id in self.reserved_planets:
            self.reserved_planets.remove(id)

        else:
            assert False, 'Tried to unreserve a planet that is not reserved'

    def is_reserved(self, p: Planet) -> bool:
        return p.id in self.reserved_planets


@dataclass
class Send():
    src: Planet
    target: Planet
    ships: Ships
    prio: int
    name: str  # the strat name
    on_discard: Optional[Callable] = None
    on_send: Optional[Callable] = None

    def encode(self):
        ships = self.ships
        src = self.src.id
        target = self.target.id
        return f'send {src} {target} {ships[0]} {ships[1]} {ships[2]}'

    def __str__(self):
        return f'{self.name:15s}: {self.encode()}'


class Nop():
    prio = 99
    name = 'Nop'

    def encode(self):
        return 'nop'


def friendly(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id == s.player_id:
            yield p


def unfriendly(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id != s.player_id:
            yield p


def neutrals(s: GameState) -> Iterable[Planet]:
    for p in s.planets:
        if p.owner_id == 0:
            yield p


def incoming_fleets(s: GameState, planet: Planet) -> Iterable[Fleet]:
    for f in s.fleets:
        if f.target_id == planet.id:
            yield f


def has_incoming_friendly_fleet(s: GameState, target: Planet):
    inc = incoming_fleets(s, target)
    inc = list(filter(lambda f: f.owner_id == s.player_id, inc))
    return len(inc) > 0


def has_incoming_enemy_fleet(s: GameState, target: Planet):
    inc = incoming_fleets(s, target)
    inc = list(filter(lambda f: f.owner_id != s.player_id, inc))
    return len(inc) > 0


def strat_capture_simple(sp: GameStatePer, s: GameState) -> Move:
    best_from, best_to, best_dist = None, None, 0
    for target in unfriendly(s):
        for mine in friendly(s):
            dist = sp.dist(mine, target)

            if sp.is_reserved(mine):
                continue

            if best_from is not None and best_dist <= dist:
                continue

            if has_incoming_friendly_fleet(s, target):
                continue

            # will win
            result = simulate_fight(mine, target)
            if result_defender_wins(*result):
                continue

            best_from, best_to, best_dist = mine, target, dist

    if best_from is not None:
        return Send(best_from, best_to, best_from.ships, PRIO_CAPTURE_SIMPLE,
                    'CaptureSimple')

    else:
        return Nop()


@dataclass
class StratCaptureMultiPlanetState():
    src_1st_id: int
    src_2nd_id: int
    target_id: int
    send_round: int  # when send the second planet's fleet. 0 means inactive

    def tick(self, sp: GameStatePer, s: GameState) -> Move:
        if self.active:
            src_1st = s.planet_get(self.src_1st_id)
            src_2nd = s.planet_get(self.src_2nd_id)
            target = s.planet_get(self.target_id)

            ongoing_fleet = self.ongoing_fleet(s)
            if ongoing_fleet is None:
                print("cancel multi attack cause ongoing fleet lost")
                self.cancel(sp)
                return Nop()

            # NOTE check if will still win
            delay = ongoing_fleet.eta - s.round
            src2_ships = src_2nd.ships_in(delay)
            ships = ships_add(src2_ships, ongoing_fleet.ships)
            result = simulate_fight(src_2nd, target, ships, delay)
            if result_defender_wins(*result):
                print("Cancel multi attack cause defender will win")
                self.cancel(sp)
                return Nop()

            if s.round < self.send_round:
                # Do not nothing. Were waiting
                return Nop()

            # it's a timing dependent attack thus prio 4
            move = Send(
                src_2nd,
                target,
                src_2nd.ships,
                PRIO_CAPTURE_MULTI_2ND,
                'CaptureMultiSend2',
                on_discard=lambda sp, s: self.cancel(sp),
                on_send=lambda sp, s: self.cancel(sp),
            )
            return move

        if not self.active:
            friendly_: List[Planet] = list(friendly(s))
            unfriendly_: List[Planet] = list(unfriendly(s))

            if len(friendly_) < 2:
                return Nop()

            moves = []  # were the possible attacks are kept
            for target in unfriendly_:

                if has_incoming_enemy_fleet(s, target):
                    continue

                for src1 in friendly_:
                    src1: Planet

                    if sp.is_reserved(src1):
                        continue

                    for src2 in friendly_:
                        src2: Planet

                        if sp.is_reserved(src2):
                            continue

                        if src1.id == src2.id:
                            continue

                        # src 1 is always farther to target
                        delay1 = src1.distance(target)
                        delay2 = src2.distance(target)
                        if delay1 < delay2:
                            continue

                        # can't perform this strat if both dists are equal
                        if delay1 == delay2:
                            continue

                        if has_incoming_friendly_fleet(s, target):
                            continue

                        # if I will win

                        delay_until_launch2 = delay1 - delay2
                        src2_ships = src2.ships_in(delay_until_launch2)
                        ships = ships_add(src1.ships, src2_ships)
                        result = simulate_fight(src2, target, ships, delay1)
                        if result_defender_wins(*result):
                            continue

                        # a possible move
                        losses = sum(ships_sub(ships, result[0]))
                        move = (
                            target,
                            src1,
                            src2,
                            delay1,
                            delay2,
                            delay_until_launch2,
                            losses,
                        )
                        moves.append(move)

            if len(moves) == 0:
                return Nop()

            # Find best move of the ones available (by loss)

            moves.sort(key=lambda x: x[6])  # sort by losses
            move = moves[-1]
            target, src1, src2, delay1, delay2, delay_until_launch2, losses = move

            self.src_1st_id = src1.id
            self.src_2nd_id = src2.id
            self.target_id = target.id
            self.send_round = s.round + delay_until_launch2

            return Send(
                src1,
                target,
                src1.ships,
                PRIO_CAPTURE_MULTI_START,
                'CaptureMultiStart',
                on_discard=self.on_discard,
                on_send=self.on_send,
            )

        assert False

    def ongoing_fleet(self, s: GameState) -> Optional[Fleet]:
        for f in s.fleets:
            if f.origin_id == self.src_1st_id and f.target_id == self.target_id:
                return f

        return None

    def on_send(self, sp: GameStatePer, s: GameState):
        sp.reserve(self.src_2nd_id)

    def on_discard(self, sp: GameStatePer, s: GameState):
        self.send_round = 0

    def cancel(self, sp: GameStatePer):
        if self.active:
            stats.CaptureMultiCancel += 1
            sp.unreserve(self.src_2nd_id)
            self.send_round = 0

    @property
    def active(self) -> bool:
        return self.send_round != 0


def strat_bailout(sp: GameStatePer, s: GameState) -> Move:
    attacked_planets: Set[Planet] = set()
    attacking_fleets: List[Fleet] = list()

    for fleet in s.fleets:
        is_friendly = fleet.owner_id == s.player_id
        if is_friendly:
            continue

        target = s.planet_get(fleet.target_id)
        if target.owner_id != s.player_id:
            continue

        attacked_planets.add(target)
        attacking_fleets.append(fleet)

    for fleet in attacking_fleets:
        # only bail if attack eminent
        delay = fleet.eta - s.round
        if delay > 4:
            continue

        origin = s.planet_get(fleet.origin_id)
        target = s.planet_get(fleet.target_id)
        result = simulate_fight(origin, target, fleet.ships)
        if result_defender_wins(*result):
            continue

        production = target.ships_produced_in(delay)
        bailed = ships_lt(target.ships, production)
        if bailed:
            continue

        safe_planets = list(
            filter(lambda p: p not in attacked_planets, friendly(s)))
        safe_planets.sort(key=lambda p: sp.dist(target, p))

        if len(safe_planets) == 0:
            continue

        planet = safe_planets[0]

        return Send(
            target,
            planet,
            target.ships,
            PRIO_BAILOUT,
            'Bailout',
        )

    return Nop()


def log(data):
    cols_names = [f.name for f in fields(Stats)]
    try:
        exists = not os.path.exists(CSV_FILE)
        with open(CSV_FILE, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=cols_names)
            if not exists:
                writer.writeheader()
            writer.writerow(data)
    except IOError:
        print("I/O error")


def simulate_fight(src: Planet, target: Planet, ships=None, delay=None):
    '''
    coputes the battle result of attackign from `src` to `target` with ships after `delay` ticks


    if ships is None, assumes all from the srcc are sent
    if delay is None, assumes distance from `src` to `target`
    '''

    if ships is None:
        attacker = src.ships
    else:
        attacker = ships

    if delay is None:
        delay = src.distance(target)

    ships_inc = [0, 0, 0]
    for i in range(3):
        ships_inc[i] = delay * target.production[i]

    defender = [0, 0, 0]
    for i in range(3):
        defender[i] = target.ships[i] + ships_inc[i]

    src_result, target_result = battle(attacker, defender)

    return src_result, target_result


def troops_needed(src_planet, target_planet, ships):
    distance = src_planet.distance(target_planet)
    ship_inc = [distance * p for p in target_planet.production]

    attacker = src_planet.ships
    defender = [n + ship_inc[i] + 1 for i, n in enumerate(target_planet.ships)]

    return defender


def result_defender_wins(src, target) -> bool:
    return sum(target) >= sum(src)


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


def battle(s1, s2):
    ships1 = s1[::]
    ships2 = s2[::]
    while sum(ships1) > 0 and sum(ships2) > 0:
        new1 = battle_round(ships2, ships1)
        ships2 = battle_round(ships1, ships2)
        ships1 = new1
        #print ships1,ships2

    ships1 = map(int, ships1)
    ships2 = map(int, ships2)
    #print ships1,ships2
    return ships1, ships2


class Agent():
    def __init__(self):
        self.sp = GameStatePer()
        self.s: Optional[GameState] = None

    def tick(self, raw: dict) -> Union[Send, Nop]:
        s = GameState.load(raw)
        self.s = s

        self.sp.init(s)
        sp = self.sp

        if s.over:
            if s.winner == s.player_id:
                stats.Victory = True
                print('Victory')
            else:
                print('Defeat')

            for p in s.players:
                if p.id != s.player_id:
                    stats.Opponent = p.name
                    break

            log(asdict(stats))
            return Nop()

        # STRATS
        moves = []
        moves.append(strat_capture_simple(sp, s))

        scmps: StratCaptureMultiPlanetState = self.sp.strat_states[
            StratCaptureMultiPlanetState.__name__]
        moves.append(scmps.tick(sp, s))

        # NOTE reevaluate bailout
        # moves.append(strat_bailout(sp, s))

        # PICKING one

        moves.sort(key=lambda x: x.prio)
        move = moves.pop(0)

        strat_name = move.name
        count = getattr(stats, strat_name)
        setattr(stats, strat_name, count + 1)

        for m in moves:
            if isinstance(m, Send) and m.on_discard is not None:
                m.on_discard(sp, s)

        if isinstance(move, Send) and move.on_send is not None:
            move.on_send(sp, s)

        return move

#!/usr/bin/env python3

import socket, json
import random, pprint

from shared import GameState, Fleet, Planet

#import view
#view.init(1024, 768)

USERNAME = "testing123123"
PASSWORD = "asdasdasdewbhdvsfk"

URL = 'localhost'
URL = "rps.vhenne.de"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((URL, 6000))
io = s.makefile('rw')


def write(data):
    io.write('%s\n' % (data, ))
    io.flush()
    print("SENDING ", data)


def main():

    write('login %s %s' % (USERNAME, PASSWORD))

    while 1:
        data = io.readline().strip()
        if not data:
            print("waaait")
            continue
            break
        elif data[0] == "{":
            state = json.loads(data)
            #        view.update(state)
            pprint.pprint(state)
            print()

            gstate = GameState.load(state)
            print(gstate)

            print()

            if state['winner'] is not None or state['game_over']:
                print("final: %s" % state['winner'])
                break

            player_id = state['player_id']

            enemy_planets = [
                planet for planet in state['planets']
                if planet['owner_id'] != player_id
            ]
            my_planets = [(sum(planet['ships']), planet)
                          for planet in state['planets']
                          if planet['owner_id'] == player_id]
            my_planets.sort(key=lambda d: d[0])

            write("nop")

            # if not my_planets:
            #     write("nop")
            # elif not enemy_planets:
            #     write("nop")
            # else:
            #     best_planet = my_planets[-1][1]
            #     target_planet = random.choice(enemy_planets)

            #     write("send %s %s %d %d %d" % (
            #         best_planet['id'],
            #         target_planet['id'],
            #         best_planet['ships'][0]/6,
            #         best_planet['ships'][1]/6,
            #         best_planet['ships'][2]/6))
        else:
            print(data)


if __name__ == '__main__':
    main()

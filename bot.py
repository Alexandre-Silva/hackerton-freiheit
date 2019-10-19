#!/usr/bin/env python3

import socket, json
import random, pprint
import sys

from shared import GameState, Fleet, Planet, Agent

#import view
#view.init(1024, 768)

USERNAME = sys.argv[1]
PASSWORD = sys.argv[2]

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

    agent = Agent()

    while 1:
        data = io.readline().strip()
        if not data:
            print("waaait")
            continue
            break

        elif data[0] == "{":
            state_raw = json.loads(data)
            #        view.update(state)
            # pprint.pprint(state)

            move = agent.tick(state_raw)

            if agent.s.over:
                break

            write(str(move))

        else:
            print(data)


def best_planet(gstate):
    b_planet = 0
    for id, planet in enumerate(gstate.planets):
        c = planet.comp(gstate.planets[b_planet])
        if c > 0:
            b_planet = id

    return b_planet


if __name__ == '__main__':
    main()

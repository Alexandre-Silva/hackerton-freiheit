#!/usr/bin/env python3

import time
import socket, json
import random, pprint
import sys
import os
import time

from shared import GameState, Fleet, Planet, Agent, Nop

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
    if 'QUIET' not in os.environ:
        print("SENDING ", data)


def main():

    write('login %s %s' % (USERNAME, PASSWORD))

    agent = Agent()

    while 1:
        data = io.readline().strip()
        if not data:
            print("waaait - failed to register")
            sys.exit()
            continue

        elif data[0] == "{":
            state_raw = json.loads(data)
            #        view.update(state)
            # pprint.pprint(state)

            move = agent.tick(state_raw)

            if not isinstance(move, Nop):
                print(f'{agent.s.round:03d} {move}')

            if agent.s.over:
                break

            write(move.encode())

        else:
            if data == 'command received. waiting for other player...':
                continue
            elif data == 'calculating round':
                print('.')

                continue

            elif data =='waaait':
                print(data)
                s.close()
                sys.exit(1)

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

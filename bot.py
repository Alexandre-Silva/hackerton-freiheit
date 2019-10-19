#!/usr/bin/env python3

import socket, json
import random, pprint

from shared import GameState, Fleet, Planet, Agent

#import view
#view.init(1024, 768)

USERNAME = "alex-test"
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

            write(move)

        else:
            print(data)


if __name__ == '__main__':
    main()

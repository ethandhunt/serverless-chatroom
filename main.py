import socket
import threading
import time
import random

# get ip
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
IP = s.getsockname()[0]
s.close()

HEADER = 60
PORT = 8081
VERSION = 'x.00'
print(f'Starting serverless chatroom version: {VERSION}')
print(f'This clients ip is {IP}')
print(f'This node hostname is {socket.gethostname()}')

# protocol_prefixes
#   MESSAGE:     |   'n_'
#   USRMESSAGE:  |   'u_'
#   BROADCAST:   |   'b_'

MESSAGE_STACK = []
BROADCAST_STACK = []
# MY_NODES is a list of machines using this machine as the interface for the network
MY_NODES = []
# Can just be an array of strings by using {TYPE}_{IP}_{MESSAGE_NUM}_{CONTENT} format
SENT_MESSAGES = []
MESSAGE_NUM = 0

# work with strings instead of bytes
# low level functions
def receiveL(s):
    temp = s.recv(HEADER)
    if temp.decode() == '':
        return False
    try:
        length = int(temp.decode())
        msg = s.recv(length)
        return msg.decode()
    except ValueError:
        print('===! Missed Package !===')
        receiveL(s)
    
def sendL(s, msg, ST=0.01):
    msg_bytes = msg.encode()
    length = str(len(msg_bytes)).zfill(HEADER)
    length_bytes = length.encode()
    s.send(length_bytes)
    s.send(msg_bytes)

# use a stack system for messages, seperate stack for each type of prefix
# when a new node is found, run this thread on its connection
def stack_listen(s):
    global MESSAGE_STACK
    while True:
        try:
            message = receiveL(s)
        except ConnectionResetError:
            message = False
        if message == False:
            MY_NODES.remove(s)
            print('Node removed')
            return
        if message[:2] == 'n_':
            MESSAGE_STACK += [message[2:]]
        elif message[:2] == 'u_':
            print(message[2:])
        elif message[:2] == 'b_':
            reBroadcast(message)


def broadcast(string):
    for s in MY_NODES:
        sendL(s, string)

def reBroadcast(string):
    if string not in SENT_MESSAGES:
        broadcast(string)
        SENT_MESSAGES.append(string)
        BROADCAST_STACK.append(string)

def broadcast_global(string):
    global MESSAGE_NUM
    message = f'b_{IP}_<{MESSAGE_NUM}>_{string}'
    reBroadcast(message)
    MESSAGE_NUM += 1

def notif_input():
    if notif_ready:
        return

    def do():
        global notif_ready
        notif_ready = True
        while True:
            broadcast_global(input(''))
    do()

def notif_handler():
    global MESSAGE_STACK
    while True:
        if MESSAGE_STACK != []:
            print(MESSAGE_STACK[0])
            MESSAGE_STACK = MESSAGE_STACK[1:]

def broadcast_handler():
    global BROADCAST_STACK
    while True:
        if BROADCAST_STACK != []:
            printMessage = BROADCAST_STACK[0].split('_')
            printMessage[3] = '_'.join(printMessage[3:])
            printMessage = printMessage[:4]
            thinga = '{'
            thingb = '}'
            print(f'{thinga}BROADCAST{thingb} @{printMessage[1]} n{printMessage[2]} < | >  {printMessage[3]}')
            BROADCAST_STACK = BROADCAST_STACK[1:]


# chat room network (lan)
# each has a socket server
# you have to get hostname of a machine to join network
# will have a broadcast protocol, so that each machine on the network gets each message

# ======= threaded functions =======

def start_thread(target, *args, **kwargs):
    threading.Thread(target=target, args=args, kwargs=kwargs).start()

def node_listener():
    print('node_listener started')
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', PORT))
    server.listen(100)
    while True:
        conn = server.accept()[0] # full is [conn, addr] but I don't use addr
        MY_NODES.append(conn)
        start_thread(stack_listen, conn)
        sendL(conn, 'u_attach registered')
        start_thread(notif_input)

def join(ip):
    print(f'attaching to {ip}')
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((ip, PORT))
    MY_NODES.append(server)
    sendL(server, f'u_{IP} attached to you')
    start_thread(stack_listen, server)
    start_thread(notif_input)


notif_ready = False
stillSending = 0
start_thread(node_listener)
start_thread(notif_handler)
start_thread(broadcast_handler)
try:
    join(socket.gethostbyaddr(input('Enter hostname for node: '))[2][0])
except KeyboardInterrupt:
    print('\n=== Node joiner thread ended ===')

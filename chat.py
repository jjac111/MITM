from diffie_hellman import DH_exchanger
from config import *
import socket


def ask_dns(name):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    soc.connect((dns_ip, ports['dns']))

    soc.send(name.encode('utf-8'))
    friend_ip = soc.recv(msg_length).decode('utf-8')
    friend_ip, friend_port = friend_ip.split(':')

    print(f'Requested DNS for {friend_name}. Redirected to {friend_ip} ...')

    return friend_ip, int(friend_port)


class Chat(object):
    def __init__(self, me_start, soc, my_name, friend_name, dh, encrypt=True):
        self.me_start = me_start
        self.soc = soc
        self.my_name = my_name
        self.friend_name = friend_name
        self.dh = dh
        self.encrypt = encrypt

    def send(self):
        msg = input(f'{self.my_name.ljust(10)}: ')
        msg_encrypted = self.dh.encrypt(msg.encode('utf-8'))
        self.soc.send(msg_encrypted if self.encrypt else msg.encode('utf-8'))
        if 'exit' == msg:
            return True

    def receive(self):
        msg = self.soc.recv(msg_length)
        msg_decrypted = self.dh.decrypt(msg).decode('utf-8')
        print(f'{self.friend_name.ljust(10)}: {msg_decrypted if self.encrypt else msg.decode("utf-8")}')
        if 'exit' == msg:
            return True

    def start(self):
        if me_start:
            while True:
                exit = self.send()
                if exit:
                    break
                exit = self.receive()
                if exit:
                    break
        else:
            while True:
                exit = self.receive()
                if exit:
                    break
                exit = self.send()
                if exit:
                    break

        self.soc.close()


if __name__ == "__main__":
    while True:
        print()
        print()
        my_name = input('Who am I?: ')

        me_start = input('Would you like to start a chat with someone? [Y] Chat or [N] Wait for someone: ')
        if 'y' in me_start.lower():
            me_start = True
        elif 'n' in me_start.lower():
            me_start = False
        else:
            print('Wrong answer.')
            continue

        encrypt_always = True if 'y' in input('Do you want to encrypt your messages? [Y/N]: ').lower() else False

        if me_start:
            friend_name = input('Who would you like to chat with?: ')
            friend_ip, friend_port = ask_dns(friend_name)

            if not friend_ip:
                print('The DNS server could not find that person.')
                continue

            p1 = 17
            p2 = 23
            private = privates[my_name]
            dh = DH_exchanger(p1, p2, private)

            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            soc.connect((friend_ip, friend_port))

            soc.send(my_name.encode('utf-8'))
            recv_name = soc.recv(msg_length).decode('utf-8')
            print(f'CONNECTED WITH {recv_name}')

            primes = f'{p1} {p2}'.encode('utf-8')
            soc.send(primes)
            print(f'SENT PRIMES: {p1} {p2}')

            friend_partial_key = int(soc.recv(msg_length).decode('utf-8'))
            my_partial_key = dh.generate_partial_key()
            soc.send(str(my_partial_key).encode('utf-8'))
            print(f'SENT PARTIAL KEY: {my_partial_key}')

            dh.generate_full_key(friend_partial_key)
            print(f'DIFFIE HELLMAN COMPLETE!\n')


        else:
            server_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_soc.bind((my_ip, ports[my_name]))
            server_soc.listen()
            print('Waiting for someone to chat with us...')
            soc, friend_addr = server_soc.accept()

            friend_name = soc.recv(msg_length).decode('utf-8')
            soc.send(my_name.encode('utf-8'))
            print(f'CONNECTED WITH {friend_name}')

            primes = soc.recv(msg_length).decode('utf-8')
            p1, p2 = primes.split()
            p1, p2 = int(p1), int(p2)
            private = privates[my_name]
            dh = DH_exchanger(p1, p2, private)

            print(f'RECEIVED PRIMES: {p1} {p2}')

            my_partial_key = dh.generate_partial_key()
            soc.send(str(my_partial_key).encode('utf-8'))
            friend_partial_key = int(soc.recv(msg_length).decode('utf-8'))
            print(f'RECEIVED PARTIAL KEY: {friend_partial_key}')

            dh.generate_full_key(friend_partial_key)
            print(f'DIFFIE HELLMAN COMPLETE!\n')

        chat = Chat(me_start=me_start, soc=soc, my_name=my_name, friend_name=friend_name, dh=dh, encrypt=encrypt_always)

        chat.start()

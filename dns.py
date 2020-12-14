import socket
from config import my_ip, ports, msg_length


def handle_request(req_soc):
    friend_name = req_soc.recv(msg_length).decode('utf-8')

    with open('dns_config', 'r') as f:
        ips = {l.split('=')[0]: l.split('=')[1] for l in f.readlines()}

    friend_ip = ips.get(friend_name)

    req_soc.send(friend_ip.encode('utf-8'))

    return friend_name, friend_ip


class DNS(object):

    def start(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        soc.bind((my_ip, ports['dns']))
        soc.listen()
        print('Waiting for DNS requests...')
        while True:
            req_soc, req_addr = soc.accept()

            friend_name, friend_ip = handle_request(req_soc)

            print(f'Request from {req_addr} to connect to {friend_name}. Redirecting to {friend_ip} ...')


if __name__ == '__main__':
    dns = DNS()

    dns.start()

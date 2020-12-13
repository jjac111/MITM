from des import DesKey

class DH_exchanger(object):
    def __init__(self, p1, p2, private):
        self.p1 = p1
        self.p2 = p2
        self.private = private
        self.full_key = None

    def generate_partial_key(self):
        partial_key = self.p1 ** self.private
        partial_key = partial_key % self.p2
        return partial_key

    def generate_full_key(self, partial_key_r):
        full_key = partial_key_r ** self.private
        full_key = full_key % self.p2
        self.full_key = bytes(str(full_key).ljust(24), encoding='utf-8')
        return full_key

    def encrypt(self, message):
        key = self.full_key

        key = DesKey(key)
        encrypted = key.encrypt(message, padding=True)

        return encrypted

    def decrypt(self, encrypted):
        key = self.full_key

        key = DesKey(key)
        decrypted = key.decrypt(encrypted, padding=True)

        return decrypted
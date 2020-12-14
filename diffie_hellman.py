from des import DesKey

class DH_exchanger(object):
    def __init__(self, p1, p2, private):
		# Initialize de algorithm on one side with the needed primes and the private number
        self.p1 = p1
        self.p2 = p2
        self.private = private
        self.key = None

    def generate_partial_key(self):
		# Generate the partial key to send to the other user
        partial_key = self.p1 ** self.private
        partial_key = partial_key % self.p2
        return partial_key

    def generate_full_key(self, friend_partial_key):
		# With the received partial key, generate the full key, which is the same for both users.
        key = friend_partial_key ** self.private
        key = key % self.p2
		# We must set the padding to make the key of a fized size 24 bytes. DES requires this.
        self.key = bytes(str(key).ljust(24), encoding='utf-8')
        return key

    def encrypt(self, message):
        key = DesKey(self.key)
        encrypted = key.encrypt(message, padding=True)

        return encrypted

    def decrypt(self, encrypted):
        key = DesKey(self.key)
        decrypted = key.decrypt(encrypted, padding=True)

        return decrypted
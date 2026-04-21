import socket
import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 1. ключи
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# 2. подключение
client = socket.socket()
client.connect(("127.0.0.1", 5000))

# 3. обмен ключами
server_public_bytes = client.recv(1024)
client.send(public_bytes)

server_public_key = serialization.load_pem_public_key(server_public_bytes)

# 4. общий секрет
shared_key = private_key.exchange(ec.ECDH(), server_public_key)

# 5. ключ для AES
derived_key = HKDF(
    algorithm=hashes.SHA256(), length=32, salt=None, info=b"handshake"
).derive(shared_key)

aes = AESGCM(derived_key)

# 6. шифруем сообщение
message = b"hello, brother"
nonce = os.urandom(12)

ciphertext = aes.encrypt(nonce, message, None)

# 7. отправляем
client.send(nonce)
client.send(ciphertext)

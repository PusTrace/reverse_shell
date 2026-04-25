from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
from dataclasses import dataclass
from pydantic import BaseModel

app = FastAPI()


class BroadcastMessage(BaseModel):
    type: str = "message"
    payload: str


class user(BaseModel):
    ws: object
    addr: str
    hostname: str


class ConnectionManager:
    def __init__(self):
        self.clients = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        client = user(
            ws=websocket,
            addr=f"{websocket.client.host}:{websocket.client.port}",
            hostname="?",
        )

        self.clients.append(client)

        print(f"[+] новый клиент: {client.addr}")

    def disconnect(self, websocket: WebSocket):
        self.clients = [c for c in self.clients if c.ws != websocket]

    def get_client(self, websocket: WebSocket):
        for c in self.clients:
            if c.ws == websocket:
                return c
        return None

    async def update_user(self, websocket: WebSocket, payload):
        client = self.get_client(websocket)
        if not client:
            return
        hostname = payload.get("hostname")
        client.hostname = hostname

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))

    async def send_to_all(self, message: dict):
        for client in self.clients:
            try:
                await client.ws.send_text(json.dumps(message))
            except:
                pass


manager = ConnectionManager()


@app.websocket("/wss")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            await handle_response(ws, data)

    except WebSocketDisconnect:
        manager.disconnect(ws)
        print("клиент отключился")


@app.post("/broadcast")
async def send_message(data: BroadcastMessage):
    message = {"type": data.type, "payload": data.payload}

    await manager.send_to_all(message)

    return {"status": "sent", "clients": len(manager.clients)}


async def handle_response(ws: WebSocket, data: str):
    client = manager.get_client(ws)
    addr = client.addr if client else "unknown"
    hostname = client.hostname if client else "unknown"

    try:
        msg = json.loads(data)
    except json.JSONDecodeError:
        print(f"[{addr}] invalid json: {data}")
        return
    msg_type = msg.get("type")
    payload = msg.get("payload", {})

    # INIT
    if msg_type == "live":
        print(f"[LIVE] {payload}")

        response = {"type": "live_ack", "payload": "connected"}
        await manager.update_user(ws, payload)
        await manager.send_to(ws, response)
        return

    # CLIENT LINE
    if msg_type == "client_line":
        print(f"{hostname}@{addr}> {payload}")
        return

    # DEFAULT
    print(f"[{addr}] {msg}")

    response = {"type": "error", "payload": "unknown message type"}

    await manager.send_to(ws, response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="server.key",
        ssl_certfile="server.crt",
    )

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

recaudado_actual = 859000

@app.get("/")
def root():
    return {"estado": "Servidor de Lina funcionando 🐶"}

# Puerta 1: Escucha a Mercado Pago
@app.post("/webhook-mp")
async def webhook_mp(request: Request):
    global recaudado_actual
    datos = await request.json()
    print("Pago recibido en Mercado Pago:", datos)
    # Temporal: suma $15.000 por cada aviso de MP
    recaudado_actual += 15000 
    await manager.broadcast({"nuevo_total": recaudado_actual})
    return {"status": "ok"}

# Puerta 2: Escucha a PayPal
@app.post("/webhook-paypal")
async def webhook_paypal(request: Request):
    global recaudado_actual
    datos = await request.json()
    print("Pago recibido en PayPal:", datos)
    # Temporal: suma $10.000 por cada aviso de PayPal
    recaudado_actual += 10000 
    await manager.broadcast({"nuevo_total": recaudado_actual})
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

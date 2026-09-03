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
        # NUEVO: Apenas alguien entra a la página, le mandamos el total actual
        await websocket.send_json({"nuevo_total": recaudado_actual})

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

@app.post("/webhook-mp")
async def webhook_mp(request: Request):
    global recaudado_actual
    
    # NUEVO: Blindaje contra formatos raros de Mercado Pago
    try:
        datos = await request.json()
        print("✅ Pago de MP (JSON):", datos)
    except:
        datos = await request.body()
        print("⚠️ Pago de MP (Texto/Form):", datos)

    recaudado_actual += 15000 
    await manager.broadcast({"nuevo_total": recaudado_actual})
    return {"status": "ok"}

@app.post("/webhook-paypal")
async def webhook_paypal(request: Request):
    global recaudado_actual
    try:
        datos = await request.json()
        print("✅ Pago de PayPal:", datos)
    except:
        pass
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

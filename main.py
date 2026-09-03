from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

# Permitir que React (que corre en otro puerto) se comunique con este servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestor de WebSockets para enviar mensajes en tiempo real
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# Variable temporal para guardar el monto (luego usaremos una base de datos)
recaudado_actual = 859000

@app.get("/")
def root():
    return {"estado": "Servidor de Lina funcionando 🐶"}

# Ruta Webhook: Aquí Mercado Pago enviará los avisos de nuevos pagos
@app.post("/webhook")
async def recibir_pago(request: Request):
    global recaudado_actual
    datos = await request.json()
    
    # Por ahora, simularemos que cada vez que entra un aviso, suman $10.000
    print("Aviso recibido desde Mercado Pago:", datos)
    recaudado_actual += 10000 
    
    # Transmitimos el nuevo total a todos los usuarios conectados
    await manager.broadcast({"nuevo_total": recaudado_actual})
    
    return {"status": "ok"}

# Ruta WebSocket: Por aquí se conectará React para escuchar
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
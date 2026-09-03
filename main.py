import json
import urllib.request
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
        await websocket.send_json({"nuevo_total": recaudado_actual})

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

recaudado_actual = 859000
# PEGA TU TOKEN AQUÍ (MANTÉN LAS COMILLAS)
ACCESS_TOKEN = "APP_USR-1516518507014771-090315-4fbc6f089ec6211569cd72f2e177f260-2424638049" 

@app.get("/")
def root():
    return {"estado": "Servidor de Lina funcionando 🐶"}

# Blindado para aceptar pruebas y pagos reales sin errores
@app.api_route("/webhook-mp", methods=["GET", "POST"])
async def webhook_mp(request: Request):
    global recaudado_actual
    try:
        pago_id = request.query_params.get("id") or request.query_params.get("data.id")
        
        if not pago_id and request.method == "POST":
            datos = await request.json()
            pago_id = datos.get("data", {}).get("id")
            
        if pago_id and pago_id != "123456": 
            url = f"https://api.mercadopago.com/v1/payments/{pago_id}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
            
            with urllib.request.urlopen(req) as response:
                info_pago = json.loads(response.read())
                
                if info_pago.get("status") == "approved":
                    monto = info_pago.get("transaction_amount", 0)
                    recaudado_actual += monto
                    print(f"✅ ¡Radar IPN detectó donación por ${monto}! Total: ${recaudado_actual}")
                    await manager.broadcast({"nuevo_total": recaudado_actual})
    except Exception as e:
        print("Error en Radar:", e)
        
    return {"status": "ok"}

@app.api_route("/webhook-paypal", methods=["GET", "POST"])
async def webhook_paypal(request: Request):
    global recaudado_actual
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

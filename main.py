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

# Variables de la campaña
recaudado_actual = 859000
# PEGA TU TOKEN AQUÍ ABAJO (MANTÉN LAS COMILLAS)
ACCESS_TOKEN = "APP_USR-1516518507014771-090315-4fbc6f089ec6211569cd72f2e177f260-2424638049" 

@app.get("/")
def root():
    return {"estado": "Servidor de Lina funcionando 🐶"}

@app.post("/webhook-mp")
async def webhook_mp(request: Request):
    global recaudado_actual
    try:
        datos = await request.json()
        
        # 1. Verificamos que sea un aviso de pago
        if datos.get("type") == "payment" or "payment" in datos.get("action", ""):
            pago_id = datos.get("data", {}).get("id")
            
            # 2. Ignoramos el pago falso de prueba de Mercado Pago
            if pago_id and pago_id != "123456": 
                
                # 3. Le preguntamos a MP el monto real usando tu Token
                url = f"https://api.mercadopago.com/v1/payments/{pago_id}"
                req = urllib.request.Request(url)
                req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
                
                with urllib.request.urlopen(req) as response:
                    info_pago = json.loads(response.read())
                    estado = info_pago.get("status")
                    monto = info_pago.get("transaction_amount", 0)
                    
                    # 4. Si el pago fue aprobado, lo sumamos!
                    if estado == "approved":
                        recaudado_actual += monto
                        print(f"✅ ¡Pago real aprobado por ${monto}! Total: ${recaudado_actual}")
                        await manager.broadcast({"nuevo_total": recaudado_actual})
    except Exception as e:
        print("Error procesando webhook MP:", e)
        
    return {"status": "ok"}

@app.post("/webhook-paypal")
async def webhook_paypal(request: Request):
    global recaudado_actual
    try:
        datos = await request.json()
        print("✅ Pago de PayPal recibido")
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

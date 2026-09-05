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

# --- CLAVES DEL SISTEMA ---
ACCESS_TOKEN = "APP_USR-1516518507014771-090315-4fbc6f089ec6211569cd72f2e177f260-2424638049" 
JSONBIN_URL = "https://api.jsonbin.io/v3/b/6a99dca5da38895dfe357ee6"
JSONBIN_KEY = "$2a$10$/0nJy8Q4XqskjU42a5Nxeuq4PDVnF5y1m8J6O1Rqovtz0GC3pG4.y"

# --- FUNCIONES DEL NOTEPAD EN LA NUBE ---
def leer_total_guardado():
    try:
        req = urllib.request.Request(JSONBIN_URL)
        req.add_header("X-Master-Key", JSONBIN_KEY)
        with urllib.request.urlopen(req) as response:
            datos = json.loads(response.read())
            return datos["record"]["total"]
    except Exception as e:
        print("Error leyendo JSONBin (usando respaldo):", e)
        return 1255000

def guardar_nuevo_total(monto):
    try:
        req = urllib.request.Request(JSONBIN_URL, data=json.dumps({"total": monto}).encode("utf-8"), method="PUT")
        req.add_header("X-Master-Key", JSONBIN_KEY)
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req)
        print("✅ Nuevo total guardado en la nube para siempre.")
    except Exception as e:
        print("Error guardando en JSONBin:", e)

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

# Al encender el servidor, lee el bloc de notas
recaudado_actual = leer_total_guardado()

@app.get("/")
def root():
    return {"estado": f"Servidor de Lina funcionando. Recaudado: ${recaudado_actual}"}

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
                    
                    # Guardamos permanentemente y avisamos a la web
                    guardar_nuevo_total(recaudado_actual)
                    await manager.broadcast({"nuevo_total": recaudado_actual})
    except Exception as e:
        print("Error en Radar:", e)
        
    return {"status": "ok"}

@app.api_route("/webhook-paypal", methods=["GET", "POST"])
async def webhook_paypal(request: Request):
    global recaudado_actual
    try:
        datos = await request.json()
        tipo_evento = datos.get("event_type")
        
        # PayPal avisa cuando el pago se completó con éxito
        if tipo_evento in ["PAYMENT.CAPTURE.COMPLETED", "PAYMENT.SALE.COMPLETED"]:
            
            # Extraemos el monto en dólares de la estructura que manda PayPal
            recurso = datos.get("resource", {})
            monto = recurso.get("amount", {})
            monto_usd = float(monto.get("value") or monto.get("total") or 0)
            
            if monto_usd > 0:
                # Conversión automática: 1 Dólar = 900 Pesos (puedes cambiar este número)
                monto_clp = int(monto_usd * 900)
                
                recaudado_actual += monto_clp
                
                # Guardamos permanentemente y avisamos a la web
                guardar_nuevo_total(recaudado_actual)
                await manager.broadcast({"nuevo_total": recaudado_actual})
                print(f"✅ ¡PayPal detectó ${monto_usd} USD! Sumando ${monto_clp} CLP. Total: ${recaudado_actual}")

    except Exception as e:
        print("Error procesando PayPal:", e)
        
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

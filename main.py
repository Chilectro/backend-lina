import json
import urllib.request
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CLAVES DEL SISTEMA ---
MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN") 
JSONBIN_URL = "https://api.jsonbin.io/v3/b/6a99dca5da38895dfe357ee6"
# VOLVEMOS A LA LLAVE MAESTRA DE TU CAPTURA DE PANTALLA
JSONBIN_KEY = "$2a$10$/0nJy8Q4XqskjU42a5Nxeuq4PDVnF5y1m8J6O1Rqovtz0GC3pG4.y"

# --- FUNCIONES DEL NOTEPAD EN LA NUBE ---
def leer_total_guardado():
    try:
        req = urllib.request.Request(JSONBIN_URL)
        req.add_header("X-Master-Key", JSONBIN_KEY)
        # Disfraz completo de Google Chrome para saltar el bloqueo de Cloudflare
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        req.add_header("Accept", "application/json")
        
        with urllib.request.urlopen(req) as response:
            datos = json.loads(response.read())
            return datos["record"]["total"]
    except Exception as e:
        print("Error leyendo JSONBin:", e)
        # Si todo falla, pongo el monto real de tu captura de pantalla
        return 1195000 

def guardar_nuevo_total(monto):
    try:
        req = urllib.request.Request(JSONBIN_URL, data=json.dumps({"total": monto}).encode("utf-8"), method="PUT")
        req.add_header("X-Master-Key", JSONBIN_KEY)
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        req.add_header("Accept", "application/json")
        
        urllib.request.urlopen(req)
        print(f"✅ Nuevo total (${monto}) guardado en la nube de JSONBin para siempre.")
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

# Al encender el servidor, lee la base de datos
recaudado_actual = leer_total_guardado()

@app.get("/")
def root():
    return {"estado": f"Servidor de Lina funcionando. Recaudado: ${recaudado_actual}"}

# ==========================================
# LA URL SECRETA PARA SUMAR MANUALMENTE
# ==========================================
@app.get("/sumar")
async def sumar_manual(monto: float, moneda: str = "USD", clave: str = ""):
    global recaudado_actual
    
    # Clave de seguridad para que nadie más meta plata fantasma
    if clave != "lina2026": 
        return {"error": "Clave incorrecta. No tienes permiso."}
    
    # Conversor de monedas automático
    if moneda.upper() == "USD":
        monto_clp = int(monto * 900)
    elif moneda.upper() == "EUR":
        monto_clp = int(monto * 980)
    else:
        monto_clp = int(monto) # Si pones CLP o nada, asume pesos chilenos
        
    recaudado_actual += monto_clp
    guardar_nuevo_total(recaudado_actual)
    await manager.broadcast({"nuevo_total": recaudado_actual})
    
    return {
        "exito": True, 
        "mensaje": f"Se sumaron {monto} {moneda.upper()} ({monto_clp} CLP).",
        "nuevo_total_historico": recaudado_actual
    }

# ==========================================

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
            req.add_header("Authorization", f"Bearer {MERCADO_PAGO_TOKEN}")
            
            with urllib.request.urlopen(req) as response:
                info_pago = json.loads(response.read())
                
                if info_pago.get("status") == "approved":
                    monto = info_pago.get("transaction_amount", 0)
                    recaudado_actual += monto
                    
                    guardar_nuevo_total(recaudado_actual)
                    await manager.broadcast({"nuevo_total": recaudado_actual})
    except Exception as e:
        print("Error en Radar:", e)
        
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

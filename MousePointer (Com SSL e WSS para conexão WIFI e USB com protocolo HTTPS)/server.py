"""
Servidor WebSocket com SSL/WSS
Controla mouse e teclado via Wi-Fi e USB
"""

import asyncio
import json
import logging
import ssl
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

PORT = 8765
TOKEN = "1234"
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

mouse = MouseController()
keyboard = KeyboardController()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --- SSL context ---
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)


async def handle_client(ws):
    peer = ws.remote_address
    logging.info(f"🔌 Cliente conectado: {peer}")
    authenticated = False

    try:
        while True:
            try:
                message = await ws.recv()
            except (ConnectionClosedOK, ConnectionClosedError):
                logging.info(f"🔒 Cliente desconectou: {peer}")
                break

            try:
                data = json.loads(message)
            except Exception as e:
                logging.warning(f"JSON inválido: {e}")
                continue

            if data.get("type") == "disconnect":
                logging.info(f"🔌 Cliente solicitou desconexão: {peer}")
                break

            if not authenticated:
                if data.get("type") == "auth" and data.get("token") == TOKEN:
                    authenticated = True
                    await ws.send(json.dumps({"type": "auth", "status": "ok"}))
                    logging.info(f"✅ Cliente autenticado: {peer}")
                else:
                    await ws.send(json.dumps({"type": "auth", "status": "fail"}))
                    logging.warning(f"❌ Token inválido de {peer}, desconectando.")
                    break
                continue

            t = data.get("type")

            if t == "move":
                dx = float(data.get("dx", 0))
                dy = float(data.get("dy", 0))
                sens = float(data.get("sensitivity", 1.0))
                try:
                    x, y = mouse.position
                    mouse.position = (x + dx * sens, y + dy * sens)
                except:
                    pass

            elif t == "click":
                btn = data.get("button", "left")
                clicks = int(data.get("clicks", 1))
                b = Button.left if btn == "left" else Button.right
                for _ in range(clicks):
                    mouse.click(b, 1)

            elif t == "scroll":
                dx = float(data.get("dx", 0))
                dy = float(data.get("dy", 0))
                mouse.scroll(dx, dy)

            elif t == "type":
                keyboard.type(data.get("text", ""))

            elif t == "gyro":
                dx = float(data.get("dx", 0))
                dy = float(data.get("dy", 0))
                try:
                    x, y = mouse.position
                    mouse.position = (x + dx, y + dy)
                except Exception as e:
                    logging.warning(f"Erro ao mover mouse via giroscópio: {e}")

    except Exception as e:
        logging.error(f"❗ Erro inesperado com {peer}: {e}")

    finally:
        logging.info(f"🔚 Finalizando conexão com {peer}")
        try:
            await ws.close()
        except:
            pass


async def main():
    logging.info(f"🚀 Servidor WSS iniciado na porta {PORT}")
    async with serve(handle_client, "0.0.0.0", PORT, ssl=ssl_context):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Servidor encerrado pelo usuário.")

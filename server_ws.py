"""
Servidor WebSocket sem SSL
Controla mouse e teclado via Wi-Fi e USB
Inclui suporte a MACROS (corrigido)
"""

import asyncio
import json
import logging
import time
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

PORT = 8765
TOKEN = "1234"

mouse = MouseController()
keyboard = KeyboardController()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# ---------------------------------------------------------
# 🔑 Mapa de teclas especiais para MACROS
# ---------------------------------------------------------
SPECIAL_KEYS = {
    "CTRL": Key.ctrl,
    "SHIFT": Key.shift,
    "ALT": Key.alt,
    "TAB": Key.tab,
    "ESC": Key.esc,
    "ENTER": Key.enter,
    "SPACE": Key.space,
    "UP": Key.up,
    "DOWN": Key.down,
    "LEFT": Key.left,
    "RIGHT": Key.right,
    "BACKSPACE": Key.backspace,
    "DELETE": Key.delete,
    "HOME": Key.home,
    "END": Key.end,
    "PAGEUP": Key.page_up,
    "PAGEDOWN": Key.page_down,
    "CAPSLOCK": Key.caps_lock,
    "F1": Key.f1, "F2": Key.f2, "F3": Key.f3, "F4": Key.f4,
    "F5": Key.f5, "F6": Key.f6, "F7": Key.f7, "F8": Key.f8,
    "F9": Key.f9, "F10": Key.f10, "F11": Key.f11, "F12": Key.f12,
}


async def handle_client(ws):
    peer = ws.remote_address
    logging.info(f"🔌 Cliente conectado: {peer}")

    authenticated = False
    start_time = time.time()

    # --- TIMER PARA O CLIENTE ---
    async def session_timer():
        while True:
            try:
                elapsed = time.time() - start_time
                await ws.send(json.dumps({
                    "type": "session_time",
                    "seconds": elapsed
                }))
                await asyncio.sleep(0.5)
            except:
                break

    timer_task = asyncio.create_task(session_timer())

    try:
        while True:
            try:
                message = await ws.recv()
            except (ConnectionClosedOK, ConnectionClosedError):
                logging.info(f"🔒 Cliente desconectou: {peer}")
                break

            try:
                data = json.loads(message)
            except:
                logging.warning("JSON inválido recebido.")
                continue

            # Pedir desconexão
            if data.get("type") == "disconnect":
                logging.info(f"🔌 Cliente solicitou desconexão: {peer}")
                break

            # --- AUTENTICAÇÃO ---
            if not authenticated:
                if data.get("type") == "auth" and data.get("token") == TOKEN:
                    authenticated = True
                    await ws.send(json.dumps({"type": "auth", "status": "ok"}))
                    logging.info(f"✅ Cliente autenticado: {peer}")
                else:
                    await ws.send(json.dumps({"type": "auth", "status": "fail"}))
                    logging.warning(f"❌ Token inválido de {peer}")
                    break
                continue

            # --- EVENTOS DE CONTROLE ---
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
                mouse.scroll(
                    float(data.get("dx", 0)),
                    float(data.get("dy", 0))
                )

            elif t == "type":
                keyboard.type(data.get("text", ""))

            elif t == "gyro":
                dx = float(data.get("dx", 0))
                dy = float(data.get("dy", 0))
                try:
                    x, y = mouse.position
                    mouse.position = (x + dx, y + dy)
                except:
                    pass

            # ----------------------------------------------------
            # 🎵 CONTROLE DE MULTIMÍDIA 
            # ----------------------------------------------------
            elif t == "media":
                action = data.get("action")

                try:
                    if action == "playpause":
                        keyboard.press(Key.media_play_pause)
                        keyboard.release(Key.media_play_pause)

                    elif action == "next":
                        keyboard.press(Key.media_next)
                        keyboard.release(Key.media_next)

                    elif action == "prev":
                        keyboard.press(Key.media_previous)
                        keyboard.release(Key.media_previous)

                    elif action == "mute":
                        keyboard.press(Key.media_volume_mute)
                        keyboard.release(Key.media_volume_mute)

                    elif action == "volup":
                        keyboard.press(Key.media_volume_up)
                        keyboard.release(Key.media_volume_up)

                    elif action == "voldown":
                        keyboard.press(Key.media_volume_down)
                        keyboard.release(Key.media_volume_down)

                    logging.info(f"🎵 Multimídia executada: {action}")

                except Exception as e:
                    logging.warning(f"Erro ao executar ação multimídia: {e}")


            # ----------------------------------------------------
            # ⭐ SUPORTE A MACROS (CORRIGIDO)
            # ----------------------------------------------------
            elif t == "macro":
                raw = data.get("keys", "")

                # Aceitar tanto lista ["CTRL","C"] quanto "CTRL+C"
                if isinstance(raw, list):
                    parts = raw
                else:
                    parts = [p.strip() for p in raw.upper().split("+")]

                logging.info(f"⚡ Macro recebida: {parts}")

                pressed = []

                # Pressionar teclas na ordem
                for p in parts:
                    key = SPECIAL_KEYS.get(p, None)

                    if key is None:
                        if len(p) == 1:
                            key = p.lower()
                        else:
                            logging.warning(f"❓ Tecla não reconhecida: {p}")
                            continue

                    try:
                        keyboard.press(key)
                        pressed.append(key)
                    except Exception as e:
                        logging.warning(f"⚠ Erro ao pressionar '{p}': {e}")

                # Soltar teclas na ordem inversa
                for k in reversed(pressed):
                    try:
                        keyboard.release(k)
                    except:
                        pass

                logging.info(f"⚡ Macro executada: {' + '.join(parts)}")

    except Exception as e:
        logging.error(f"❗ Erro inesperado com {peer}: {e}")

    finally:
        timer_task.cancel()
        logging.info(f"⏱️ Sessão durou {time.time() - start_time:.2f}s")

        try:
            await ws.close()
        except:
            pass

        

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
async def main():
    logging.info(f"🚀 Servidor WS iniciado na porta {PORT}")
    async with serve(handle_client, "0.0.0.0", PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Servidor encerrado pelo usuário.")

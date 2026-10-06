import argparse
import json
import threading
import time
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

class SimulatorState:
    def __init__(self):
        self.lock = threading.Lock()
        self.turnstiles = {}

    def register_turnstile(
        self,
        turnstile_id,
        device_id,
        gateway,
        callback_url
    ):
        with self.lock:
            if turnstile_id not in self.turnstiles:
                self.turnstiles[turnstile_id] = {}

            self.turnstiles[turnstile_id].update(
                {
                    "turnstile_id": turnstile_id,
                    "device_id": str(device_id),
                    "gateway": gateway,
                    "callback_url": callback_url,
                    "unlocked": False,
                    "allow": "both",
                    "passage_timeout": 5.0,
                    "released_at": None,
                    "last_message": "Aguardando QR..."
                }
            )

    def release_turnstile(
        self,
        turnstile_id,
        allow,
        passage_timeout
    ):
        with self.lock:
            if turnstile_id not in self.turnstiles:
                raise KeyError(turnstile_id)

            self.turnstiles[turnstile_id]["unlocked"] = True
            self.turnstiles[turnstile_id]["allow"] = allow
            self.turnstiles[turnstile_id]["passage_timeout"] = float(passage_timeout)
            self.turnstiles[turnstile_id]["released_at"] = time.time()
            self.turnstiles[turnstile_id]["last_message"] = "Liberada. Escolha ENTRADA, SAÍDA ou DESISTIR."

    def expire_if_needed(self):
        now = time.time()

        with self.lock:
            for item in self.turnstiles.values():
                if not item.get("unlocked"):
                    continue

                released_at = item.get("released_at")
                timeout = float(item.get("passage_timeout", 5.0))

                if released_at is None:
                    continue

                if now - released_at >= timeout:
                    item["unlocked"] = False
                    item["last_message"] = "Tempo expirado. Aguardando próximo QR."

    def snapshot(self):
        self.expire_if_needed()

        with self.lock:
            return {
                turnstile_id: dict(data)
                for turnstile_id, data in self.turnstiles.items()
            }

    def set_message_and_lock(
        self,
        turnstile_id,
        message
    ):
        with self.lock:
            item = self.turnstiles[turnstile_id]
            item["unlocked"] = False
            item["released_at"] = None
            item["last_message"] = message

class SimulatorGUI:
    def __init__(
        self,
        state
    ):
        self.state = state
        self.root = tk.Tk()
        self.root.title("Simulador de Catracas")
        self.cards = {}

        self.header = tk.Label(
            self.root,
            text="Simulador visual de catracas",
            font=("Arial", 14, "bold")
        )
        self.header.pack(pady=10)

        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        self.footer = tk.Label(
            self.root,
            text="Quando uma catraca for liberada pelo A2, use os botões abaixo para simular o giro.",
            anchor="w",
            justify="left"
        )
        self.footer.pack(fill="x", padx=10, pady=(0, 10))

        self.root.after(200, self.refresh)

    def post_turn_event(
        self,
        turnstile_id,
        logical_direction
    ):
        snapshot = self.state.snapshot()
        item = snapshot[turnstile_id]

        if not item.get("unlocked"):
            return

        gateway = item["gateway"]

        if logical_direction == "entrada":
            event_name = "TURN_RIGHT" if gateway == "clockwise" else "TURN_LEFT"
            message = "Passagem simulada: ENTRADA."
        else:
            event_name = "TURN_LEFT" if gateway == "clockwise" else "TURN_RIGHT"
            message = "Passagem simulada: SAÍDA."

        payload = {
            "device_id": item["device_id"],
            "event": {
                "name": event_name
            }
        }

        try:
            requests.post(
                item["callback_url"],
                json=payload,
                timeout=3
            ).raise_for_status()

            self.state.set_message_and_lock(
                turnstile_id,
                message
            )

        except Exception as e:
            self.state.set_message_and_lock(
                turnstile_id,
                f"Erro ao enviar evento: {e}"
            )

    def post_give_up(
        self,
        turnstile_id
    ):
        snapshot = self.state.snapshot()
        item = snapshot[turnstile_id]

        if not item.get("unlocked"):
            return

        payload = {
            "device_id": item["device_id"],
            "event": {
                "name": "GIVE_UP"
            }
        }

        try:
            requests.post(
                item["callback_url"],
                json=payload,
                timeout=3
            ).raise_for_status()

            self.state.set_message_and_lock(
                turnstile_id,
                "Desistência simulada."
            )

        except Exception as e:
            self.state.set_message_and_lock(
                turnstile_id,
                f"Erro ao enviar desistência: {e}"
            )

    def build_card(
        self,
        parent,
        turnstile_id
    ):
        frame = tk.LabelFrame(
            parent,
            text=turnstile_id,
            padx=10,
            pady=10
        )

        labels = {
            "device_id": tk.Label(frame, anchor="w", justify="left"),
            "gateway": tk.Label(frame, anchor="w", justify="left"),
            "status": tk.Label(frame, anchor="w", justify="left", font=("Arial", 10, "bold")),
            "message": tk.Label(frame, anchor="w", justify="left", wraplength=450),
            "timeout": tk.Label(frame, anchor="w", justify="left")
        }

        for key in ("device_id", "gateway", "status", "message", "timeout"):
            labels[key].pack(fill="x", pady=2)

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))

        buttons = {
            "entrada": tk.Button(
                button_frame,
                text="Girar para ENTRADA",
                command=lambda tid=turnstile_id: self.post_turn_event(tid, "entrada")
            ),
            "saida": tk.Button(
                button_frame,
                text="Girar para SAÍDA",
                command=lambda tid=turnstile_id: self.post_turn_event(tid, "saida")
            ),
            "give_up": tk.Button(
                button_frame,
                text="Desistir",
                command=lambda tid=turnstile_id: self.post_give_up(tid)
            )
        }

        buttons["entrada"].pack(side="left", padx=4)
        buttons["saida"].pack(side="left", padx=4)
        buttons["give_up"].pack(side="left", padx=4)

        frame.pack(fill="x", pady=6)

        self.cards[turnstile_id] = {
            "frame": frame,
            "labels": labels,
            "buttons": buttons
        }

    def refresh(self):
        snapshot = self.state.snapshot()

        for turnstile_id in snapshot:
            if turnstile_id not in self.cards:
                self.build_card(self.container, turnstile_id)

        for turnstile_id, item in snapshot.items():
            card = self.cards[turnstile_id]
            labels = card["labels"]
            buttons = card["buttons"]

            labels["device_id"].config(text=f"device_id: {item['device_id']}")
            labels["gateway"].config(text=f"gateway (sentido de ENTRADA): {item['gateway']}")

            if item.get("unlocked"):
                status_text = "Status: LIBERADA"
                remaining = max(
                    0.0,
                    float(item["passage_timeout"]) - (time.time() - float(item["released_at"]))
                )
                timeout_text = f"Tempo restante: {remaining:.1f} s"
                state = "normal"
            else:
                status_text = "Status: BLOQUEADA"
                timeout_text = "Tempo restante: -"
                state = "disabled"

            labels["status"].config(text=status_text)
            labels["message"].config(text=item.get("last_message", ""))
            labels["timeout"].config(text=timeout_text)

            for button in buttons.values():
                button.config(state=state)

        self.root.after(200, self.refresh)

    def run(self):
        self.root.mainloop()

def create_http_server(
    state,
    host,
    port
):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"status": "ok"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            path = self.path.split("?")[0]

            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            try:
                if path == "/register":
                    state.register_turnstile(
                        turnstile_id=payload["turnstile_id"],
                        device_id=payload["device_id"],
                        gateway=payload.get("gateway", "clockwise"),
                        callback_url=payload["callback_url"]
                    )

                elif path == "/release":
                    state.release_turnstile(
                        turnstile_id=payload["turnstile_id"],
                        allow=payload.get("allow", "both"),
                        passage_timeout=payload.get("passage_timeout", 5)
                    )

                else:
                    self.send_response(404)
                    self.end_headers()
                    return

            except KeyError:
                self.send_response(404)
                self.end_headers()
                return

            response = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    return ThreadingHTTPServer((host, port), Handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    state = SimulatorState()
    server = create_http_server(state, args.host, args.port)

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )
    thread.start()

    print(f"Simulador visual ouvindo em http://{args.host}:{args.port}")

    gui = SimulatorGUI(state)

    try:
        gui.run()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()

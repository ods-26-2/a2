import argparse
import json
import threading
import time
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer
)
from urllib.request import (
    Request,
    urlopen
)


HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">
<title>Catraca pelo celular</title>
<style>
body {
  font-family: Arial, sans-serif;
  margin: 0;
  background: #111827;
  color: #f9fafb;
}
main {
  max-width: 520px;
  margin: 0 auto;
  padding: 24px;
}
.card {
  background: #1f2937;
  border-radius: 18px;
  padding: 22px;
  margin-top: 20px;
}
h1 { font-size: 25px; }
.status {
  font-size: 30px;
  font-weight: bold;
  text-align: center;
  padding: 28px 10px;
}
.meta {
  line-height: 1.7;
  color: #d1d5db;
}
button {
  width: 100%;
  padding: 18px;
  margin-top: 12px;
  border: 0;
  border-radius: 12px;
  font-size: 19px;
  font-weight: bold;
}
.entrada { background: #22c55e; }
.saida { background: #60a5fa; }
.desistir { background: #f87171; }
button:disabled {
  opacity: .35;
}
#mensagem {
  margin-top: 16px;
  text-align: center;
  min-height: 24px;
}
</style>
</head>
<body>
<main>
  <h1>Simulador de Catraca</h1>

  <div class="card">
    <div id="status"
         class="status">
      AGUARDANDO...
    </div>

    <div class="meta">
      <div>Catraca:
        <b id="catraca">-</b>
      </div>
      <div>Device ID:
        <b id="device">-</b>
      </div>
      <div>Tempo:
        <b id="tempo">-</b>
      </div>
    </div>

    <button id="entrada"
            class="entrada"
            onclick="evento('entrada')">
      ENTRADA
    </button>

    <button id="saida"
            class="saida"
            onclick="evento('saida')">
      SAÍDA
    </button>

    <button id="desistir"
            class="desistir"
            onclick="evento('give_up')">
      DESISTIR
    </button>

    <div id="mensagem"></div>
  </div>
</main>

<script>
async function atualizar() {
  try {
    const r = await fetch('/status');
    const s = await r.json();

    document.getElementById('catraca')
      .textContent = s.turnstile_id || '-';

    document.getElementById('device')
      .textContent = s.device_id || '-';

    document.getElementById('tempo')
      .textContent =
        s.unlocked
          ? s.remaining.toFixed(1) + ' s'
          : '-';

    document.getElementById('status')
      .textContent =
        s.unlocked
          ? '🔓 LIBERADA'
          : '🔒 BLOQUEADA';

    document.getElementById('mensagem')
      .textContent = s.message || '';

    for (const id of
         ['entrada','saida','desistir']) {
      document.getElementById(id)
        .disabled = !s.unlocked;
    }
  } catch (e) {
    document.getElementById('status')
      .textContent = 'SEM CONEXÃO';
  }
}

async function evento(direction) {
  const r = await fetch('/event', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      direction: direction
    })
  });

  const data = await r.json()
    .catch(() => ({}));

  if (!r.ok) {
    alert(
      data.error ||
      'Falha ao enviar evento.'
    );
  }

  atualizar();
}

setInterval(atualizar, 350);
atualizar();
</script>
</body>
</html>
"""


class MobileState:
    def __init__(self):
        self.lock = threading.Lock()

        self.turnstile_id = None
        self.device_id = None
        self.gateway = "clockwise"
        self.callback_url = None

        self.unlocked = False
        self.allow = "both"
        self.deadline = None
        self.message = (
            "Aguardando configuração do A2."
        )

    def configure(
        self,
        turnstile_id,
        device_id,
        gateway,
        callback_url
    ):
        if gateway not in (
            "clockwise",
            "anticlockwise"
        ):
            raise ValueError(
                "gateway inválido"
            )

        with self.lock:
            self.turnstile_id = (
                str(turnstile_id)
            )

            self.device_id = (
                str(device_id)
            )

            self.gateway = gateway
            self.callback_url = (
                str(callback_url)
            )

            self.unlocked = False
            self.deadline = None

            self.message = (
                "Configurada. "
                "Aguardando QR válido."
            )

    def release(
        self,
        allow,
        passage_timeout
    ):
        if allow not in (
            "clockwise",
            "anticlockwise",
            "both"
        ):
            raise ValueError(
                "allow inválido"
            )

        with self.lock:
            if (
                self.device_id is None
                or self.callback_url is None
            ):
                raise RuntimeError(
                    "Celular ainda não "
                    "foi configurado pelo A2."
                )

            self.allow = allow
            self.unlocked = True

            self.deadline = (
                time.time()
                + float(
                    passage_timeout
                )
            )

            self.message = (
                "Liberada. Escolha "
                "ENTRADA, SAÍDA ou DESISTIR."
            )

    def expire_if_needed(self):
        with self.lock:
            if (
                self.unlocked
                and self.deadline
                is not None
                and time.time()
                >= self.deadline
            ):
                self.unlocked = False
                self.deadline = None
                self.message = (
                    "Tempo expirado. "
                    "Aguardando novo QR."
                )

    def snapshot(self):
        self.expire_if_needed()

        with self.lock:
            remaining = 0.0

            if (
                self.unlocked
                and self.deadline
                is not None
            ):
                remaining = max(
                    0.0,
                    self.deadline
                    - time.time()
                )

            return {
                "turnstile_id":
                    self.turnstile_id,

                "device_id":
                    self.device_id,

                "unlocked":
                    self.unlocked,

                "remaining":
                    remaining,

                "message":
                    self.message
            }

    def prepare_event(
        self,
        direction
    ):
        self.expire_if_needed()

        with self.lock:
            if not self.unlocked:
                raise RuntimeError(
                    "Catraca bloqueada."
                )

            if (
                direction
                == "give_up"
            ):
                event_name = "GIVE_UP"

            elif direction in (
                "entrada",
                "saida"
            ):
                if (
                    direction
                    == "entrada"
                ):
                    rotation = (
                        self.gateway
                    )
                else:
                    rotation = (
                        "anticlockwise"
                        if self.gateway
                        == "clockwise"
                        else "clockwise"
                    )

                if (
                    self.allow
                    != "both"
                    and rotation
                    != self.allow
                ):
                    raise RuntimeError(
                        "Sentido não liberado."
                    )

                event_name = (
                    "TURN_RIGHT"
                    if rotation
                    == "clockwise"
                    else "TURN_LEFT"
                )

            else:
                raise ValueError(
                    "direction inválida"
                )

            return (
                self.callback_url,
                self.device_id,
                event_name
            )

    def finish_event(
        self,
        direction
    ):
        with self.lock:
            self.unlocked = False
            self.deadline = None

            if direction == "entrada":
                self.message = (
                    "Passagem simulada: ENTRADA."
                )
            elif direction == "saida":
                self.message = (
                    "Passagem simulada: SAÍDA."
                )
            else:
                self.message = (
                    "Passagem cancelada."
                )


def post_callback(
    callback_url,
    device_id,
    event_name
):
    payload = json.dumps(
        {
            "device_id":
                device_id,

            "event": {
                "name":
                    event_name
            }
        }
    ).encode(
        "utf-8"
    )

    request = Request(
        callback_url,
        data=payload,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urlopen(
        request,
        timeout=5
    ) as response:
        response.read()


def create_server(
    host,
    port
):
    state = MobileState()

    class Handler(
        BaseHTTPRequestHandler
    ):
        def send_json(
            self,
            status,
            payload
        ):
            body = json.dumps(
                payload,
                ensure_ascii=False
            ).encode(
                "utf-8"
            )

            self.send_response(
                status
            )

            self.send_header(
                "Content-Type",
                "application/json; "
                "charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(
                    len(body)
                )
            )

            self.end_headers()

            self.wfile.write(
                body
            )

        def do_GET(self):
            path = self.path.split(
                "?"
            )[0]

            if path == "/":
                body = HTML.encode(
                    "utf-8"
                )

                self.send_response(
                    200
                )

                self.send_header(
                    "Content-Type",
                    "text/html; "
                    "charset=utf-8"
                )

                self.send_header(
                    "Content-Length",
                    str(
                        len(body)
                    )
                )

                self.end_headers()

                self.wfile.write(
                    body
                )

                return

            if path == "/health":
                self.send_json(
                    200,
                    {
                        "status": "ok"
                    }
                )
                return

            if path == "/status":
                self.send_json(
                    200,
                    state.snapshot()
                )
                return

            self.send_json(
                404,
                {
                    "error":
                        "Não encontrado."
                }
            )

        def read_json(self):
            length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            raw = self.rfile.read(
                length
            )

            if not raw:
                return {}

            return json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        def do_POST(self):
            path = self.path.split(
                "?"
            )[0]

            try:
                data = self.read_json()

                if path == "/configure":
                    state.configure(
                        turnstile_id=
                            data[
                                "turnstile_id"
                            ],

                        device_id=
                            data[
                                "device_id"
                            ],

                        gateway=
                            data.get(
                                "gateway",
                                "clockwise"
                            ),

                        callback_url=
                            data[
                                "callback_url"
                            ]
                    )

                    self.send_json(
                        200,
                        {
                            "ok": True
                        }
                    )
                    return

                if path == "/release":
                    state.release(
                        allow=data.get(
                            "allow",
                            "both"
                        ),
                        passage_timeout=
                            data.get(
                                "passage_timeout",
                                5
                            )
                    )

                    self.send_json(
                        200,
                        {
                            "ok": True
                        }
                    )
                    return

                if path == "/event":
                    direction = data[
                        "direction"
                    ]

                    (
                        callback_url,
                        device_id,
                        event_name
                    ) = state.prepare_event(
                        direction
                    )

                    post_callback(
                        callback_url,
                        device_id,
                        event_name
                    )

                    state.finish_event(
                        direction
                    )

                    self.send_json(
                        200,
                        {
                            "ok": True,
                            "event":
                                event_name
                        }
                    )
                    return

                self.send_json(
                    404,
                    {
                        "error":
                            "Não encontrado."
                    }
                )

            except Exception as error:
                self.send_json(
                    400,
                    {
                        "error":
                            str(
                                error
                            )
                    }
                )

        def log_message(
            self,
            format,
            *args
        ):
            return

    return ThreadingHTTPServer(
        (
            host,
            port
        ),
        Handler
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        default="0.0.0.0"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080
    )

    args = parser.parse_args()

    server = create_server(
        args.host,
        args.port
    )

    print(
        "Catraca de celular ouvindo em "
        f"http://{args.host}:{args.port}"
    )

    print(
        "No próprio celular, abra no navegador: "
        f"http://127.0.0.1:{args.port}"
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nEncerrando catraca..."
        )

    finally:
        server.server_close()


if __name__ == "__main__":
    main()

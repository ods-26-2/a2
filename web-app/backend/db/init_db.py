import sys
import logging
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from db.connection import (
    DB_PATH,
    get_connection,
    init_db,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    force = "--populate" in sys.argv or "-p" in sys.argv or "--force" in sys.argv

    logger.info("Inicializando banco de dados SQLite em: %s", DB_PATH)
    try:
        init_db(force=force)

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cpf, is_recurring, specific_date, access_days, access_hours, active
                FROM users
                ORDER BY cpf
                """
            )
            users = cursor.fetchall()
        finally:
            conn.close()

        logger.info("Banco de dados SQLite pronto (%d usuario(s) configurado(s)).", len(users))
        for u in users:
            if not u["is_recurring"]:
                logger.info(
                    "Usuario [CPF: %s] (recorrente: False, data: %s, horarios: %s)",
                    u["cpf"],
                    u["specific_date"],
                    u["access_hours"],
                )
            else:
                logger.info(
                    "Usuario [CPF: %s] (recorrente: True, dias: %s, horarios: %s)",
                    u["cpf"],
                    u["access_days"],
                    u["access_hours"],
                )

    except Exception as e:
        logger.error("Falha ao inicializar banco de dados SQLite: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

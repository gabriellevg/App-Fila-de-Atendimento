import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fila.db"


def conectar():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    conexao = conectar()

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            status TEXT NOT NULL DEFAULT 'aguardando',
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            iniciado_em DATETIME,
            concluido_em DATETIME
        )
    """)

    conexao.commit()
    conexao.close()

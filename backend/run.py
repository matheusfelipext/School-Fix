"""
run.py — Ponto de entrada em desenvolvimento:  python run.py

Se o banco estiver vazio (primeira execução ou modo em memória), popula com os
dados de exemplo de seed.py. Em produção use gunicorn (ver Procfile).
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app, repo  # noqa: E402
from app.models import COL_USUARIOS  # noqa: E402

app = create_app()

# Popula o banco na primeira execução. Desligue com SEED_AUTOMATICO=0 (ex.: para testar do zero).
with app.app_context():
    if os.environ.get("SEED_AUTOMATICO", "1") == "1" and repo.contar(COL_USUARIOS) == 0:
        import seed
        seed.executar(silencioso=False)

if __name__ == "__main__":
    # host 127.0.0.1 (e não 0.0.0.0): se a porta já estiver ocupada por um Flask antigo,
    # o Python avisa na hora ("Address already in use") em vez de subir escondido.
    # Para acessar de outro aparelho da rede, coloque HOST=0.0.0.0 no .env.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "1") == "1")
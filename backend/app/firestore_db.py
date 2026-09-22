"""
firestore_db.py — Conexão com o Cloud Firestore.

get_db() devolve o cliente do Firestore (real ou em memória). É chamado por app/repo.py.

Modo real   → firebase_admin com a conta de serviço (FIREBASE_CREDENTIALS ou _JSON).
Modo mock   → mockfirestore.MockFirestore(): mesma API, dados só em memória.
"""
import json
import logging
import os

_db = None
_modo = None


def _iniciar(config):
    global _db, _modo
    cred_path = config.get("FIREBASE_CREDENTIALS")
    cred_json = config.get("FIREBASE_CREDENTIALS_JSON")
    usar_mock = config.get("FIRESTORE_MOCK") or not (cred_path or cred_json)

    if usar_mock:
        from mockfirestore import MockFirestore
        _db, _modo = MockFirestore(), "mock"
        if not config.get("FIRESTORE_MOCK"):
            logging.warning("FIREBASE_CREDENTIALS não definido → usando Firestore EM MEMÓRIA (dados temporários).")
        return

    import firebase_admin
    from firebase_admin import credentials, firestore

    if cred_json:
        cred = credentials.Certificate(json.loads(cred_json))
    else:
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Arquivo de credenciais do Firebase não encontrado: {cred_path}")
        cred = credentials.Certificate(cred_path)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    # O Firestore permite vários bancos por projeto; o padrão chama-se "(default)".
    # Se o banco foi criado com outro nome no console, FIRESTORE_DATABASE precisa bater com ele.
    banco = config.get("FIRESTORE_DATABASE") or "(default)"
    _db = firestore.client(database_id=banco) if banco != "(default)" else firestore.client()
    _modo = "firestore"
    logging.info("Conectado ao Cloud Firestore (projeto %s, banco %s).", cred.project_id, banco)


def init_app(app):
    _iniciar(app.config)
    app.extensions["firestore_modo"] = _modo


def get_db():
    if _db is None:
        raise RuntimeError("Firestore não inicializado. Chame firestore_db.init_app(app).")
    return _db


def modo():
    return _modo

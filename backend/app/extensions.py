"""
extensions.py — Instâncias das extensões do Flask, criadas sem app e ligadas em create_app().
(O acesso ao Firestore fica em app/firestore_db.py.)
"""
from flask_cors import CORS
from flask_jwt_extended import JWTManager

jwt = JWTManager()   # cria e valida tokens JWT
cors = CORS()        # permite o front (outra origem) chamar a API

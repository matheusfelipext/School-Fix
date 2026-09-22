"""
auth.py — Decorators de autenticação/autorização (JWT).

Fluxo: POST /api/auth/login devolve um token assinado; o front o envia em
`Authorization: Bearer <token>`. Dentro do token ficam "claims" (perfil, area_id, nome),
lidas com get_jwt() — sem consultar o banco a cada requisição.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app import repo
from app.models import COL_USUARIOS


def login_requerido(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def perfil_requerido(*perfis_permitidos):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("perfil") not in perfis_permitidos:
                return jsonify({"erro": "Você não tem permissão para acessar este recurso."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def usuario_atual() -> dict | None:
    """Documento do usuário dono do token (quando é preciso mais que as claims)."""
    return repo.obter(COL_USUARIOS, get_jwt_identity())


def perfil_atual() -> str:
    return get_jwt().get("perfil")

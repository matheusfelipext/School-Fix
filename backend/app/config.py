"""
config.py — Configurações da aplicação (lidas de variáveis de ambiente / .env).

Banco de dados: Cloud Firestore (Firebase).
  - FIREBASE_CREDENTIALS      caminho do JSON da conta de serviço (Firebase Console →
                              Configurações do projeto → Contas de serviço → Gerar nova chave)
  - FIREBASE_CREDENTIALS_JSON o conteúdo do JSON inteiro (útil no Render, que não aceita arquivo)
  - FIRESTORE_DATABASE        nome do banco no Firestore. Vazio = "(default)". Se você criou o banco
                              com outro nome no console (ex.: dbschoolfix), informe aqui.
  - FIRESTORE_MOCK=1          usa um Firestore EM MEMÓRIA (sem credenciais). Bom para testar;
                              os dados somem quando o servidor reinicia.
Se nenhuma das três estiver definida, a aplicação sobe em modo mock e avisa no console.
"""
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-troque-em-producao")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-troque-em-producao")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_HORAS", "8")))

    # Firestore
    FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS", "")
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON", "")
    FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "").strip() or "(default)"
    FIRESTORE_MOCK = os.environ.get("FIRESTORE_MOCK", "") == "1"

    # Origens permitidas no CORS ("*" em dev; em produção a URL do site)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Limite do corpo da requisição (imagens em base64). Documento do Firestore aceita até 1 MB.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

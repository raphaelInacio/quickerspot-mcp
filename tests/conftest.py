import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Adiciona o diretório do backend e do mcp-server ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
MCP_SERVER_DIR = BASE_DIR / "mcp-server"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if str(MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_DIR))

# Garante variáveis de ambiente para testes M2M e Settings
os.environ["QUICKERSPOT_API_URL"] = "http://testserver"
os.environ["QUICKERSPOT_M2M_API_KEY"] = "test_e2e_m2m_key"
os.environ["QUICKERSPOT_M2M_USER_ID"] = "test_e2e_user_id"
os.environ.setdefault("ASAAS_API_KEY_PRD", "dummy_asaas_key")
os.environ.setdefault("ASAAS_WEBHOOK_TOKEN_PRD", "dummy_webhook_token")

# Mock seguro do Firebase Admin e FirestoreSaver durante a importação do backend
import firebase_admin  # noqa: E402
from firebase_admin import firestore as admin_firestore  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

import graphs.firestore_saver  # noqa: E402

try:
    firebase_admin.get_app()
except ValueError:
    mock_app = MagicMock()
    firebase_admin.get_app = MagicMock(return_value=mock_app)
    firebase_admin.initialize_app = MagicMock(return_value=mock_app)
    mock_client = MagicMock()
    admin_firestore.client = MagicMock(return_value=mock_client)

graphs.firestore_saver.FirestoreSaver = MemorySaver

#!/usr/bin/env python3
"""
Validador de esquema do manifesto server.json para o MCP Registry.
"""

import json
import sys
from pathlib import Path
import httpx
import jsonschema

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_URL = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"


def validate_server_json(file_path: Path) -> bool:
    if not file_path.exists():
        print(f"❌ Erro: Arquivo {file_path} não encontrado.")
        return False

    print(f"🔍 Baixando o esquema oficial do MCP Registry ({SCHEMA_URL})...")
    try:
        response = httpx.get(SCHEMA_URL, timeout=10.0)
        response.raise_for_status()
        schema = response.json()
    except Exception as e:
        print(f"❌ Erro ao baixar esquema JSON: {e}")
        return False

    print(f"📄 Lendo {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("⚡ Validando o manifesto server.json contra o esquema...")
    try:
        jsonschema.validate(instance=data, schema=schema)
        print("✅ Validação concluída com SUCESSO! O manifesto server.json é 100% válido perante o MCP Registry.")
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"❌ Falha na validação do server.json:")
        print(f"   Campo: {e.json_path}")
        print(f"   Mensagem: {e.message}")
        return False


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "server.json"
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    
    success = validate_server_json(target)
    sys.exit(0 if success else 1)

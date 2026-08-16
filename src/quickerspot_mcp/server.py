"""
Servidor MCP QuickerSpot usando FastMCP.
Expõe ferramentas para criação de campanhas, roteirização com IA, sintetização de áudio e recados instantâneos.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Garantir que o diretório base mcp-server esteja no sys.path
MCP_SERVER_DIR = str(Path(__file__).resolve().parent.parent.parent)
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

try:
    from quickerspot_mcp.client import QuickerSpotAPIError, QuickerSpotClient
except ImportError:
    from src.client import QuickerSpotAPIError, QuickerSpotClient  # type: ignore[no-redef]


# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

API_URL = os.getenv("QUICKERSPOT_API_URL", "https://voz-comercial-backend-bvbcktwqoq-uc.a.run.app")
M2M_API_KEY = os.getenv("QUICKERSPOT_API_KEY") or os.getenv("QUICKERSPOT_M2M_API_KEY") or ""


# Inicializa a aplicação FastMCP
mcp = FastMCP("quickerspot")

# Instância global do cliente HTTP QuickerSpot
_client: QuickerSpotClient | None = None


def get_client() -> QuickerSpotClient:
    """Retorna ou inicializa o cliente HTTP QuickerSpot."""
    global _client
    if _client is None:
        _client = QuickerSpotClient(base_url=API_URL, api_key=M2M_API_KEY)
    return _client


@mcp.tool()
async def list_voices() -> str:
    """
    Lista todas as vozes comerciais disponíveis no QuickerSpot para narração e vinhetas.

    Utilize esta ferramenta antes de criar uma campanha ou recado para escolher
    o timbre de voz mais apropriado para o seu produto/anúncio.

    Retorna um JSON contendo uma lista de objetos com id, elevenlabs_id e name.
    """
    client = get_client()
    try:
        result = await client.list_voices()
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao listar vozes: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao listar vozes: {e!s}"


@mcp.tool()
async def create_campaign(
    name: str,
    data: list[dict[str, Any]] | None = None,
    voice_tone: str = "Friendly",
    slogan: str | None = None,
    free_text: str | None = None,
    voice_id: str | None = None,
    background_music: str | None = None,
    audio_style: str = "standard",
    production_mode: str = "standard",
) -> str:
    """
    Cria uma nova campanha comercial no QuickerSpot e gera o roteiro em formato texto via IA.

    Esta operação é síncrona para a geração do roteiro (leva de 5 a 15 segundos).
    Após a criação, o estado da campanha fica como PENDING aguardando aprovação do roteiro.

    Parâmetros:
    - name: Nome identificador da campanha (ex: "Ofertas de Fim de Semana").
    - data: Lista opcional de produtos com preços, ex: [{"product": "Detergente 500ml", "price": "R$ 2,99"}].
    - voice_tone: Tom de voz desejado (ex: "Friendly", "Enthusiastic", "Professional", "Urgent"). Default: "Friendly".
    - slogan: Slogan comercial da loja ou marca (opcional).
    - free_text: Instrução ou texto livre em formato plain text para a IA gerar o comercial (opcional se enviar data).
    - voice_id: ID da voz selecionada (consulte via `list_voices`) (opcional).
    - background_music: Trilha sonora de fundo (opcional).
    - audio_style: Estilo do áudio ("standard" | "dramatic") (opcional).
    - production_mode: Modo de produção ("standard" | "ai_production") (opcional).

    Retorna um JSON com os dados da campanha criada, o ID da campanha (`campaign_id` ou `id`) e os roteiros gerados.
    """
    client = get_client()
    payload = {
        "name": name,
        "data": data or [],
        "voice_tone": voice_tone,
        "slogan": slogan,
        "free_text": free_text,
        "voice_id": voice_id,
        "background_music": background_music,
        "audio_style": audio_style,
        "production_mode": production_mode,
    }
    try:
        result = await client.create_campaign(payload)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao criar campanha: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao criar campanha: {e!s}"


@mcp.tool()
async def approve_script(
    campaign_id: str,
    script: str | None = None,
    action: str = "approve",
) -> str:
    """
    Aprova (ou edita) o roteiro de uma campanha e dispara a produção de áudio (TTS e mixagem) em background.

    Parâmetros:
    - campaign_id: ID da campanha a ser aprovada.
    - script: Texto do roteiro final editado (opcional). Se não informado, utiliza o roteiro gerado pela IA.
    - action: Ação a realizar ("approve" para aprovar e gerar áudio, ou "regenerate" para solicitar novo roteiro). Default: "approve".

    Retorna uma confirmação de que o processamento foi iniciado em background (Status 202 Accepted).
    Use `get_campaign_status` após alguns segundos para verificar a conclusão da produção.
    """
    client = get_client()
    payload = {
        "script": script,
        "action": action,
    }
    try:
        result = await client.approve_script(campaign_id, payload)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao aprovar roteiro: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao aprovar roteiro: {e!s}"


@mcp.tool()
async def get_campaign_status(campaign_id: str) -> str:
    """
    Consulta o status atual, roteiros e links para os arquivos de áudio de uma campanha específica.

    Utilize esta ferramenta para verificar se o áudio de uma campanha já terminou de ser produzido.

    Status possíveis:
    - PENDING: Aguardando aprovação do roteiro.
    - PROCESSING: Áudio sendo gerado e mixado em background.
    - COMPLETED: Áudio gerado com sucesso. As URLs dos arquivos MP3 estão disponíveis no campo `audios`.
    - FAILED: Ocorreu uma falha durante o processamento.

    Parâmetros:
    - campaign_id: ID da campanha a ser consultada.
    """
    client = get_client()
    try:
        result = await client.get_campaign_status(campaign_id)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao consultar status da campanha: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao consultar status da campanha: {e!s}"


@mcp.tool()
async def list_campaigns() -> str:
    """
    Lista todas as campanhas comerciais pertencentes ao usuário vinculado à API Key M2M.

    Retorna uma lista em JSON com o histórico de campanhas, incluindo status e URLs de áudio.
    """
    client = get_client()
    try:
        result = await client.list_campaigns()
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao listar campanhas: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao listar campanhas: {e!s}"


@mcp.tool()
async def create_recado(
    text: str,
    voice_id: str | None = None,
) -> str:
    """
    Gera um áudio instantâneo de recado curto (fast-lane TTS sem fluxo de aprovação HITL).

    Ideal para anúncios rápidos de loja, avisos de estacionamento, chamadas de clientes ou recados operacionais.
    O áudio gerado já inclui vinheta/chime sonora no início.

    Parâmetros:
    - text: Texto do recado a ser sintetizado (máximo 300 caracteres).
    - voice_id: ID da voz (opcional).

    Retorna um JSON contendo os detalhes do áudio e a URL direta para download/reprodução do MP3.
    """
    client = get_client()
    payload = {
        "text": text,
        "voice_id": voice_id,
    }
    try:
        result = await client.create_recado(payload)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except QuickerSpotAPIError as e:
        return f"Erro ao criar recado: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"Erro inesperado ao criar recado: {e!s}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

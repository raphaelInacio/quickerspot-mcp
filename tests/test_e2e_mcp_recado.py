"""
Teste E2E para o fluxo de recados instantâneos via MCP Server.
Valida o comando: create_recado -> verificação da URL de áudio retornada.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from core.config import settings
from main import app
from models.schemas import AudioResponse, PlanType, Status, UserResponse
from src.client import QuickerSpotClient
from src.server import create_recado


@pytest.fixture
def m2m_e2e_client(monkeypatch):
    """Instancia o QuickerSpotClient apontando para o app FastAPI via ASGITransport."""
    monkeypatch.setattr(settings, "QUICKERSPOT_M2M_API_KEY", "test_e2e_m2m_key")
    monkeypatch.setattr(settings, "QUICKERSPOT_M2M_USER_ID", "test_e2e_user_id")

    transport = httpx.ASGITransport(app=app)
    async_client = httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-API-Key": "test_e2e_m2m_key"},
    )
    qs_client = QuickerSpotClient("http://testserver", "test_e2e_m2m_key", client=async_client)
    return qs_client


@pytest.mark.asyncio
async def test_e2e_mcp_recado_flow(m2m_e2e_client):
    """
    Testa o fluxo E2E de recado instantâneo via MCP Tool:
    1. create_recado: Envia um texto curto de recado
    2. Valida o retorno contendo ID do áudio, ID da campanha e URL direta do MP3 gerado
    """
    mock_user_profile = UserResponse(
        id="test_e2e_user_id",
        email="m2m_e2e@quickerspot.com",
        plan_type=PlanType.PRO,
        credits=50,
        has_valid_card=True,
    )

    mock_campaign = MagicMock()
    mock_campaign.id = "e2e_recado_camp_123"

    mock_audio_response = AudioResponse(
        id="audio_recado_e2e_1",
        campaignId="e2e_recado_camp_123",
        originalText="Atenção clientes! Oferta relâmpago no setor de hortifruti.",
        scriptedText="Atenção clientes! Oferta relâmpago no setor de hortifruti.",
        audioUrl="https://storage.googleapis.com/test-bucket/audios/e2e_recado_camp_123/audio.mp3",
        status=Status.COMPLETED,
    )

    mock_guardrail_instance = AsyncMock()
    mock_guardrail_instance.validate_brand_safety.return_value = MagicMock(
        is_safe=True, reason=None
    )

    mock_tts_instance = AsyncMock()
    mock_tts_instance.generate_audio.return_value = b"tts_audio_content"

    mock_mixer_instance = AsyncMock()
    mock_mixer_instance.mix_chime_and_tts.return_value = b"chime_and_tts_content"

    with (
        patch("src.server.get_client", return_value=m2m_e2e_client),
        patch("api.deps.FirestoreService.get_user", return_value=mock_user_profile),
        patch("api.deps.FirestoreService.count_campaigns_this_month", return_value=0),
        patch("api.v1.endpoints.m2m.AIGuardrail", return_value=mock_guardrail_instance),
        patch("api.v1.endpoints.m2m.get_tts_provider", return_value=mock_tts_instance),
        patch("api.v1.endpoints.m2m.AudioMixer", return_value=mock_mixer_instance),
        patch("api.v1.endpoints.m2m.FirestoreService.create_campaign", return_value=mock_campaign),
        patch(
            "api.v1.endpoints.m2m.StorageService.upload_audio_content",
            return_value="https://storage.googleapis.com/test-bucket/audios/e2e_recado_camp_123/audio.mp3",
        ),
        patch(
            "api.v1.endpoints.m2m.FirestoreService.add_audio_to_campaign",
            return_value=mock_audio_response,
        ),
    ):
        result_json_str = await create_recado(
            text="Atenção clientes! Oferta relâmpago no setor de hortifruti.",
            voice_id="M_Vibrant",
        )
        recado_res = json.loads(result_json_str)

        assert recado_res["id"] == "audio_recado_e2e_1"
        assert recado_res["campaignId"] == "e2e_recado_camp_123"
        assert recado_res["status"] == "COMPLETED"
        assert (
            recado_res["audioUrl"]
            == "https://storage.googleapis.com/test-bucket/audios/e2e_recado_camp_123/audio.mp3"
        )

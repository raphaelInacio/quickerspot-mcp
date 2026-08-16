"""
Teste E2E para o fluxo completo de campanha via MCP Server.
Valida o ciclo: list_voices -> create_campaign -> approve_script -> get_campaign_status -> list_campaigns.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from core.config import settings
from main import app
from models.schemas import AudioResponse, CampaignResponse, CampaignType, PlanType, Status, UserResponse
from src.client import QuickerSpotClient
from src.server import approve_script, create_campaign, get_campaign_status, list_campaigns, list_voices


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
async def test_e2e_mcp_campaign_flow(m2m_e2e_client):
    """
    Testa o fluxo E2E de campanha via MCP Tools:
    1. list_voices: Lista as vozes disponíveis
    2. create_campaign: Cria a campanha e gera o roteiro via IA (PENDING)
    3. approve_script: Aprova o roteiro e dispara o resumo no LangGraph (PROCESSING)
    4. get_campaign_status: Consulta o status da campanha finalizada (COMPLETED)
    5. list_campaigns: Verifica a listagem de campanhas
    """
    mock_user_profile = UserResponse(
        id="test_e2e_user_id",
        email="m2m_e2e@quickerspot.com",
        plan_type=PlanType.PRO,
        credits=100,
        has_valid_card=True,
    )

    created_campaign_data = {
        "id": "e2e_camp_999",
        "name": "Super Ofertas de Verão",
        "userId": "test_e2e_user_id",
        "status": "PENDING",
        "type": "standard",
        "script": "Aproveite as super ofertas de verão na nossa loja!",
        "generated_scripts": [
            {
                "product": "Sorvete",
                "script": "Aproveite as super ofertas de verão na nossa loja!",
            }
        ],
        "audios": [],
    }

    now = datetime.now(timezone.utc)

    mock_pending_campaign = CampaignResponse(
        id="e2e_camp_999",
        name="Super Ofertas de Verão",
        status=Status.PENDING,
        userId="test_e2e_user_id",
        type=CampaignType.STANDARD,
        voice_id="M_Vibrant",
        createdAt=now,
        script="Aproveite as super ofertas de verão na nossa loja!",
        generated_scripts=[
            {"product": "Sorvete", "script": "Aproveite as super ofertas de verão na nossa loja!"}
        ],
        audios=[],
    )

    mock_completed_campaign = CampaignResponse(
        id="e2e_camp_999",
        name="Super Ofertas de Verão",
        status=Status.COMPLETED,
        userId="test_e2e_user_id",
        type=CampaignType.STANDARD,
        voice_id="M_Vibrant",
        createdAt=now,
        script="Aproveite as super ofertas de verão na nossa loja!",
        generated_scripts=[
            {"product": "Sorvete", "script": "Aproveite as super ofertas de verão na nossa loja!"}
        ],
        audios=[
            {
                "id": "audio_e2e_1",
                "audioUrl": "https://storage.googleapis.com/test-bucket/audios/e2e_camp_999/audio.mp3",
            }
        ],
    )

    db_campaigns = {"e2e_camp_999": mock_pending_campaign}

    def mock_get_campaign_fn(cid):
        return db_campaigns.get(cid)

    def mock_update_status_fn(cid, new_status):
        if cid in db_campaigns:
            if new_status == Status.COMPLETED or new_status == "COMPLETED":
                db_campaigns[cid] = mock_completed_campaign

    mock_audio_completed = AudioResponse(
        id="audio_e2e_1",
        campaignId="e2e_camp_999",
        originalText="Aproveite as super ofertas de verão!",
        scriptedText="Aproveite as super ofertas de verão!",
        audioUrl="https://storage.googleapis.com/test-bucket/audios/e2e_camp_999/audio.mp3",
        status=Status.COMPLETED,
    )

    with (
        patch("src.server.get_client", return_value=m2m_e2e_client),
        patch("api.deps.FirestoreService.get_user", return_value=mock_user_profile),
        patch("api.deps.FirestoreService.count_campaigns_this_month", return_value=0),
        patch(
            "services.campaign_service.CampaignService.initialize_campaign", new_callable=AsyncMock
        ) as mock_init,
        patch(
            "api.v1.endpoints.m2m.FirestoreService.get_campaign", side_effect=mock_get_campaign_fn
        ),
        patch(
            "api.v1.endpoints.m2m.FirestoreService.list_campaigns",
            return_value=[mock_completed_campaign],
        ),
        patch(
            "api.v1.endpoints.m2m.FirestoreService.get_campaign_audios",
            return_value=[mock_audio_completed],
        ),
        patch("api.v1.endpoints.m2m.StorageService.refresh_url", side_effect=lambda url: url),
        patch("api.v1.endpoints.m2m.FirestoreService.update_campaign_script"),
        patch(
            "api.v1.endpoints.m2m.FirestoreService.update_campaign_status",
            side_effect=mock_update_status_fn,
        ),
        patch("api.v1.endpoints.m2m.orchestrator_app.update_state"),
        patch("api.v1.endpoints.m2m.orchestrator_app.ainvoke"),
    ):
        mock_init.return_value = created_campaign_data

        # Passo 1: Listar vozes disponíveis
        voices_json_str = await list_voices()
        voices_res = json.loads(voices_json_str)
        assert "voices" in voices_res
        assert len(voices_res["voices"]) > 0

        # Passo 2: Criar campanha
        create_json_str = await create_campaign(
            name="Super Ofertas de Verão",
            data=[{"product": "Sorvete", "price": "R$ 5,00"}],
            voice_tone="Enthusiastic",
            voice_id="M_Vibrant",
        )
        create_res = json.loads(create_json_str)
        assert create_res["id"] == "e2e_camp_999"
        assert create_res["status"] == "PENDING"
        assert "verão" in create_res["script"]

        # Passo 3: Aprovar Roteiro
        approve_json_str = await approve_script(
            campaign_id="e2e_camp_999",
            script="Aproveite as super ofertas de verão na nossa loja!",
            action="approve",
        )
        approve_res = json.loads(approve_json_str)
        assert approve_res["campaign_id"] == "e2e_camp_999"
        assert approve_res["status"] == "PROCESSING"

        # Simula conclusão em background
        db_campaigns["e2e_camp_999"] = mock_completed_campaign

        # Passo 4: Polling/Consulta do Status Final da Campanha
        status_json_str = await get_campaign_status(campaign_id="e2e_camp_999")
        status_res = json.loads(status_json_str)
        assert status_res["id"] == "e2e_camp_999"
        assert status_res["status"] == "COMPLETED"
        assert len(status_res["audios"]) == 1
        assert "storage.googleapis.com" in status_res["audios"][0]["audioUrl"]

        # Passo 5: Listar todas as campanhas
        list_json_str = await list_campaigns()
        list_res = json.loads(list_json_str)
        assert len(list_res) == 1
        assert list_res[0]["id"] == "e2e_camp_999"

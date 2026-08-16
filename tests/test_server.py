"""
Testes unitários para as ferramentas do servidor MCP (server.py).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.client import QuickerSpotAPIError
from src.server import (
    approve_script,
    create_campaign,
    create_recado,
    get_campaign_status,
    list_campaigns,
    list_voices,
)


@pytest.mark.asyncio
async def test_tool_list_voices_success():
    mock_client = AsyncMock()
    mock_client.list_voices.return_value = {
        "voices": [{"id": "M_Vibrant", "elevenlabs_id": "xyz", "name": "M Vibrant"}]
    }

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await list_voices()
        res = json.loads(res_str)
        assert "voices" in res
        assert res["voices"][0]["id"] == "M_Vibrant"
        mock_client.list_voices.assert_called_once()


@pytest.mark.asyncio
async def test_tool_list_voices_api_error():
    mock_client = AsyncMock()
    mock_client.list_voices.side_effect = QuickerSpotAPIError("API Key inválida", status_code=401)

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await list_voices()
        assert "Erro ao listar vozes: API Key inválida" in res_str


@pytest.mark.asyncio
async def test_tool_create_campaign_success():
    mock_client = AsyncMock()
    mock_client.create_campaign.return_value = {
        "id": "camp_123",
        "name": "Ofertas",
        "status": "PENDING",
    }

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await create_campaign(
            name="Ofertas",
            data=[{"product": "Café", "price": "R$ 15,00"}],
            voice_tone="Friendly",
        )
        res = json.loads(res_str)
        assert res["id"] == "camp_123"
        assert res["status"] == "PENDING"
        mock_client.create_campaign.assert_called_once()


@pytest.mark.asyncio
async def test_tool_create_campaign_error():
    mock_client = AsyncMock()
    mock_client.create_campaign.side_effect = QuickerSpotAPIError(
        "Dados inválidos", status_code=400
    )

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await create_campaign(name="Ofertas", data=[])
        assert "Erro ao criar campanha: Dados inválidos" in res_str


@pytest.mark.asyncio
async def test_tool_approve_script_success():
    mock_client = AsyncMock()
    mock_client.approve_script.return_value = {
        "message": "Aprovação recebida",
        "campaign_id": "camp_123",
        "status": "PROCESSING",
    }

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await approve_script(campaign_id="camp_123", script="Texto revisado")
        res = json.loads(res_str)
        assert res["campaign_id"] == "camp_123"
        assert res["status"] == "PROCESSING"
        mock_client.approve_script.assert_called_once_with(
            "camp_123", {"script": "Texto revisado", "action": "approve"}
        )


@pytest.mark.asyncio
async def test_tool_get_campaign_status_success():
    mock_client = AsyncMock()
    mock_client.get_campaign_status.return_value = {
        "id": "camp_123",
        "status": "COMPLETED",
        "audios": [{"audioUrl": "http://audio.mp3"}],
    }

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await get_campaign_status(campaign_id="camp_123")
        res = json.loads(res_str)
        assert res["status"] == "COMPLETED"
        mock_client.get_campaign_status.assert_called_once_with("camp_123")


@pytest.mark.asyncio
async def test_tool_list_campaigns_success():
    mock_client = AsyncMock()
    mock_client.list_campaigns.return_value = [{"id": "camp_1"}, {"id": "camp_2"}]

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await list_campaigns()
        res = json.loads(res_str)
        assert len(res) == 2
        mock_client.list_campaigns.assert_called_once()


@pytest.mark.asyncio
async def test_tool_create_recado_success():
    mock_client = AsyncMock()
    mock_client.create_recado.return_value = {
        "audioUrl": "http://storage/recado.mp3",
        "status": "COMPLETED",
    }

    with patch("src.server.get_client", return_value=mock_client):
        res_str = await create_recado(text="Atenção clientes!", voice_id="M_Vibrant")
        res = json.loads(res_str)
        assert res["audioUrl"] == "http://storage/recado.mp3"
        mock_client.create_recado.assert_called_once_with(
            {"text": "Atenção clientes!", "voice_id": "M_Vibrant"}
        )

"""
Testes unitários para o QuickerSpotClient (client.py).
"""

import httpx
import pytest
import respx

from src.client import QuickerSpotAPIError, QuickerSpotClient

BASE_URL = "http://localhost:8000"
API_KEY = "test-m2m-api-key"


@pytest.fixture
def client():
    return QuickerSpotClient(base_url=BASE_URL, api_key=API_KEY)


@pytest.mark.asyncio
async def test_list_voices_success(client):
    with respx.mock:
        route = respx.get(f"{BASE_URL}/v1/m2m/voices").respond(
            status_code=200,
            json={"voices": [{"id": "M_Vibrant", "elevenlabs_id": "xyz", "name": "M Vibrant"}]},
        )
        res = await client.list_voices()
        assert route.called
        assert route.calls.last.request.headers["X-API-Key"] == API_KEY
        assert "voices" in res
        assert res["voices"][0]["id"] == "M_Vibrant"
    await client.close()


@pytest.mark.asyncio
async def test_create_campaign_success(client):
    payload = {"name": "Campanha Teste", "data": [{"product": "Prod 1", "price": "10,00"}]}
    with respx.mock:
        route = respx.post(f"{BASE_URL}/v1/m2m/campaigns").respond(
            status_code=201,
            json={"id": "camp_123", "name": "Campanha Teste", "status": "PENDING"},
        )
        res = await client.create_campaign(payload)
        assert route.called
        assert res["id"] == "camp_123"
        assert res["status"] == "PENDING"
    await client.close()


@pytest.mark.asyncio
async def test_approve_script_success(client):
    campaign_id = "camp_123"
    payload = {"action": "approve", "script": "Roteiro aprovado"}
    with respx.mock:
        route = respx.post(f"{BASE_URL}/v1/m2m/campaigns/{campaign_id}/approve").respond(
            status_code=202,
            json={
                "message": "Aprovação recebida e processamento de áudio iniciado.",
                "campaign_id": campaign_id,
                "status": "PROCESSING",
                "action": "approve",
            },
        )
        res = await client.approve_script(campaign_id, payload)
        assert route.called
        assert res["campaign_id"] == campaign_id
        assert res["status"] == "PROCESSING"
    await client.close()


@pytest.mark.asyncio
async def test_get_campaign_status_success(client):
    campaign_id = "camp_123"
    with respx.mock:
        route = respx.get(f"{BASE_URL}/v1/m2m/campaigns/{campaign_id}").respond(
            status_code=200,
            json={
                "id": campaign_id,
                "status": "COMPLETED",
                "audios": [{"audioUrl": "http://storage/audio.mp3"}],
            },
        )
        res = await client.get_campaign_status(campaign_id)
        assert route.called
        assert res["id"] == campaign_id
        assert res["status"] == "COMPLETED"
    await client.close()


@pytest.mark.asyncio
async def test_list_campaigns_success(client):
    with respx.mock:
        route = respx.get(f"{BASE_URL}/v1/m2m/campaigns").respond(
            status_code=200,
            json=[{"id": "camp_1"}, {"id": "camp_2"}],
        )
        res = await client.list_campaigns()
        assert route.called
        assert len(res) == 2
        assert res[0]["id"] == "camp_1"
    await client.close()


@pytest.mark.asyncio
async def test_create_recado_success(client):
    payload = {"text": "Atenção clientes, oferta relâmpago!", "voice_id": "M_Vibrant"}
    with respx.mock:
        route = respx.post(f"{BASE_URL}/v1/m2m/recados").respond(
            status_code=201,
            json={"audioUrl": "http://storage/recado.mp3", "status": "COMPLETED"},
        )
        res = await client.create_recado(payload)
        assert route.called
        assert res["audioUrl"] == "http://storage/recado.mp3"
    await client.close()


@pytest.mark.asyncio
async def test_client_http_error_handling_401(client):
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/m2m/voices").respond(
            status_code=401, json={"detail": "Invalid API Key"}
        )
        with pytest.raises(QuickerSpotAPIError) as exc_info:
            await client.list_voices()
        assert exc_info.value.status_code == 401
        assert "Erro de Autenticação (401)" in exc_info.value.message
    await client.close()


@pytest.mark.asyncio
async def test_client_http_error_handling_404(client):
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/m2m/campaigns/inexistent").respond(
            status_code=404, json={"detail": "Campaign not found"}
        )
        with pytest.raises(QuickerSpotAPIError) as exc_info:
            await client.get_campaign_status("inexistent")
        assert exc_info.value.status_code == 404
        assert "Não Encontrado (404)" in exc_info.value.message
    await client.close()


@pytest.mark.asyncio
async def test_client_http_error_handling_402(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/m2m/recados").respond(
            status_code=402, json={"detail": "Saldo insuficiente"}
        )
        with pytest.raises(QuickerSpotAPIError) as exc_info:
            await client.create_recado({"text": "Teste"})
        assert exc_info.value.status_code == 402
        assert "Saldo Insuficiente (402)" in exc_info.value.message
    await client.close()


@pytest.mark.asyncio
async def test_client_request_error(client):
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/m2m/voices").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        with pytest.raises(QuickerSpotAPIError) as exc_info:
            await client.list_voices()
        assert "Erro de conexão" in exc_info.value.message
    await client.close()

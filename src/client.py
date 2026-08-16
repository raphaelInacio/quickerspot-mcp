"""
Cliente HTTP assíncrono para a API M2M do QuickerSpot.
"""

import logging
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)


class QuickerSpotAPIError(Exception):
    """Exceção personalizada para erros amigáveis da API do QuickerSpot."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuickerSpotClient:
    """Cliente HTTP assíncrono wrapper do httpx para os endpoints M2M."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        """Obtém ou inicializa a instância do AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Executa uma requisição HTTP e trata erros de status e conexão."""
        try:
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            detail = None
            try:
                body = exc.response.json()
                if isinstance(body, dict):
                    detail = body.get("detail")
            except (ValueError, TypeError):
                detail = exc.response.text

            if status_code == 401:
                msg = f"Erro de Autenticação (401): API Key M2M inválida. ({detail or 'Não autorizado'})"
            elif status_code == 403:
                msg = f"Erro de Permissão (403): {detail or 'Acesso negado à campanha.'}"
            elif status_code == 404:
                msg = f"Não Encontrado (404): {detail or 'Recurso ou campanha não encontrada.'}"
            elif status_code == 402:
                msg = f"Saldo Insuficiente (402): {detail or 'Créditos insuficientes.'}"
            elif status_code == 400:
                msg = f"Requisição Inválida (400): {detail or 'Dados enviados incorretos.'}"
            elif status_code == 503:
                msg = f"Serviço Indisponível (503): {detail or 'Autenticação M2M não configurada no backend.'}"
            else:
                msg = f"Erro na API QuickerSpot ({status_code}): {detail or exc!s}"

            logger.error(f"[M2M Client] HTTP {status_code}: {msg}")
            raise QuickerSpotAPIError(msg, status_code=status_code) from exc
        except httpx.RequestError as exc:
            msg = f"Erro de conexão com o backend QuickerSpot: {exc!s}"
            logger.error(f"[M2M Client] RequestError: {msg}")
            raise QuickerSpotAPIError(msg) from exc

    async def list_voices(self) -> dict[str, Any]:
        """Obtém o catálogo de vozes disponíveis para sintetização comercial."""
        return await self._request("GET", "/v1/m2m/voices")

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Cria uma nova campanha comercial e gera o roteiro via IA."""
        return await self._request("POST", "/v1/m2m/campaigns", json=payload)

    async def approve_script(self, campaign_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Aprova ou edita o roteiro de uma campanha e dispara a produção do áudio."""
        return await self._request("POST", f"/v1/m2m/campaigns/{campaign_id}/approve", json=payload)

    async def get_campaign_status(self, campaign_id: str) -> dict[str, Any]:
        """Consulta o status e detalhes de uma campanha específica pelo ID."""
        return await self._request("GET", f"/v1/m2m/campaigns/{campaign_id}")

    async def list_campaigns(self) -> list[dict[str, Any]]:
        """Lista todas as campanhas do usuário associado à API Key M2M."""
        return await self._request("GET", "/v1/m2m/campaigns")

    async def create_recado(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Gera áudio instantâneo de um recado curto (fast-lane TTS sem HITL)."""
        return await self._request("POST", "/v1/m2m/recados", json=payload)

    async def close(self) -> None:
        """Fecha o cliente HTTP se estiver aberto."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

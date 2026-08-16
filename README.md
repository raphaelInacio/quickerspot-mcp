<!-- mcp-name: io.github.raphaelInacio/quickerspot-mcp -->
mcp-name: io.github.raphaelInacio/quickerspot-mcp

# Servidor MCP QuickerSpot

Servidor oficial **Model Context Protocol (MCP)** para a plataforma [QuickerSpot](https://quickerspot.com) — Automação de vinhetas, rádio indoor e sonorização comercial com IA.

Conecte seus Assistentes de IA (Cursor IDE, Claude Desktop, Antigravity, Hermes Agent, OpenClaw) diretamente ao motor de voz ElevenLabs V3, gerador de roteiros por IA e mixer de rádio indoor do QuickerSpot.

---

## 🚀 Como Usar em 2 Passos

### 1. Obter sua API Key
Acesse o painel do QuickerSpot em **[quickerspot.com/settings](https://quickerspot.com/settings)** e crie uma nova API Key (ex: `qs_live_...`).

### 2. Configurar o mcp.json
Adicione a definição do servidor no seu arquivo `mcp.json` (ou `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quickerspot": {
      "command": "uvx",
      "args": ["quickerspot-mcp"],
      "env": {
        "QUICKERSPOT_API_KEY": "qs_live_SUA_CHAVE_AQUI"
      }
    }
  }
}
```

*O `quickerspot-mcp` conecta-se automaticamente ao backend de produção do QuickerSpot. Se você estiver desenvolvendo localmente, pode adicionar `"QUICKERSPOT_API_URL": "http://localhost:8000"` no bloco `env`.*

---

## 🛠️ Ferramentas MCP Disponíveis (`tools`)

1. **`list_voices()`** — Retorna o catálogo de vozes comerciais disponíveis (Camila, Helena, Marcos, Carlos, Ricardo).
2. **`create_campaign(name, data, voice_tone, free_text)`** — Cria uma nova campanha comercial e gera o roteiro síncrono via IA.
3. **`approve_script(campaign_id, script)`** — Aprova o roteiro e dispara a produção de áudio TTS + mixagem em background.
4. **`get_campaign_status(campaign_id)`** — Consulta o status (`PENDING`, `PROCESSING`, `COMPLETED`), roteiro e URLs de download dos MP3s.
5. **`list_campaigns()`** — Lista todas as campanhas ativas da sua conta.
6. **`create_recado(text, voice_id)`** — Gera áudio instantâneo de recado/aviso para loja com vinheta (fast-lane sem fluxo HITL).

---

## 💻 Execução com Python Local (Opcional)

Se preferir rodar localmente com Python:

```json
{
  "mcpServers": {
    "quickerspot": {
      "command": "python",
      "args": ["-m", "quickerspot_mcp.server"],
      "env": {
        "QUICKERSPOT_API_KEY": "qs_live_SUA_CHAVE_AQUI"
      }
    }
  }
}
```

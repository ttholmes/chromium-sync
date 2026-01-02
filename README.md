# Chromium Sync — Sincronização bidirecional 🔁

**Chromium Sync** é uma ferramenta para macOS que sincroniza dados entre navegadores Chromium (ex.: Dia Browser, Arc Browser, Brave, Vivaldi, Microsoft Edge, Chrome, etc), mantendo **Histórico**, **Favoritos** e **Abas** sincronizados de forma segura e confiável.

---

## 📚 Índice

- [Recursos](#-recursos)
- [Requisitos](#-requisitos)
- [Instalação rápida](#-instalação-rápida)
- [Instalação manual](#-instalação-manual)
- [Uso](#-uso)
- [Monitoramento & Logs](#-monitoramento--logs)
- [Desinstalação](#-desinstalação)
- [Aviso de Segurança](#-aviso-de-segurança)
- [Contribuição](#-contribuição)
- [Licença](#-licença)
- [Contato](#-contato)

---

## ✨ Recursos

- **Mesclagem de Histórico (bidirecional):** combina entradas de `History` preservando timestamps e visitas.
- **Sincronização de Favoritos:** replica pastas e bookmarks sem criar duplicatas.
- **Sincronização de Abas/Sessões:** detecta o navegador mais recentemente utilizado e replica abas/janelas para o outro (último modificado vence).
- **Proteções:** verifica se os navegadores estão fechados antes de operar e faz cópias temporárias para mitigar corrupção.
- **Logs e backups automáticos:** gera logs e backups antes de aplicar mudanças.

---

## 📋 Requisitos

- macOS (testado em versões recentes)
- Python 3.8+
- Dia Browser e Vivaldi instalados
- Permissões para instalar um `LaunchAgent` (opcional, para agendamento automático)

> Dica: recomendamos usar um ambiente virtual (`python3 -m venv .venv && source .venv/bin/activate`) ao testar localmente.

---

## 🚀 Instalação rápida

1. Clone o repositório:

```bash
git clone https://github.com/ttholmes/chromium-sync.git
cd chromium-sync
```

2. Execute o instalador (verifique `install.sh` antes):

```bash
chmod +x install.sh
./install.sh
```

O instalador padrão copia os scripts para `~/Scripts/chromium-sync/` (verifique o caminho), cria um `LaunchAgent` em `~/Library/LaunchAgents/` para agendamento e configura logs e backups.

---

## 🔧 Instalação manual

- Para executar sem instalar:

```bash
python3 sync_engine.py
```

- Se preferir instalar os arquivos manualmente, copie-os para a pasta desejada (ex.: `~/Scripts/chromium-sync/`) e configure um `LaunchAgent` para execução periódica.

---

## 🛠 Uso

- Execução manual (recomenda-se fechar os navegadores antes):

```bash
python3 ~/Scripts/chromium-sync/sync_engine.py
```

- Para monitorar a execução (logs):

```bash
tail -f /tmp/sync_browsers.log
```

---

## 🩺 Monitoramento & Logs

- Logs: `/tmp/sync_browsers.log`
- Verifique os backups gerados antes de qualquer alteração importante.

---

## 🧹 Desinstalação

Remova o `LaunchAgent` e os arquivos do projeto (ajuste os nomes conforme o seu ambiente):

```bash
launchctl unload ~/Library/LaunchAgents/com.user.browsersync.plist || true
rm -f ~/Library/LaunchAgents/com.user.browsersync.plist || true
rm -rf ~/Scripts/chromium-sync
```

> Atenção: backups e logs podem permanecer — remova manualmente se desejar.

---

## ❗ Aviso de segurança

Este projeto acessa e modifica bancos de dados internos do navegador (`History`, `Bookmarks`). Apesar das proteções, faça backup do perfil do navegador antes da primeira execução e revise logs se ocorrer algo inesperado. Use por sua conta e risco.

---

## 🤝 Contribuição

Contribuições são bem-vindas! Abra uma issue para discutir mudanças grandes ou envie um PR com testes e descrição das alterações.

- Por favor, inclua: descrição do problema/feature, ambiente (macOS versão, Python) e passos para reproduzir.

---

## 📝 Licença

Distribuído sob a licença **MIT** — veja `LICENSE`.

---

## ✉️ Contato

Abra uma issue neste repositório para dúvidas e relatórios de bugs.

---

*Obrigado por usar o Chromium Sync — contribuições e feedback ajudam a melhorar a ferramenta!*

# Chromium Sync — Sincronização bidirecional (Dia ↔ Vivaldi)

Ferramenta para macOS que sincroniza **bidirecionalmente** dados entre o [Dia Browser](https://diabrowser.com) e o [Vivaldi](https://vivaldi.com), mantendo **Histórico**, **Favoritos (Bookmarks)** e **Abas abertas (Open Tabs)** consistentes entre os dois navegadores.

---

## ✨ Recursos principais

- **🔄 Mesclagem de Histórico (bidirecional):** mescla os bancos SQLite de `History` mantendo timestamps e visitas.
- **🔖 Sincronização de Favoritos:** espelha pastas e bookmarks entre os navegadores sem duplicatas.
- **🧭 Sessões Inteligentes (último modificado vence):** detecta qual navegador foi usado por último e replica as abas/janelas para o outro.
- **🛡️ Segurança:** valida se os navegadores estão fechados antes de operar e faz cópias temporárias para reduzir risco de corrupção.
- **📋 Logs e backups automáticos:** registra operações e gera backups antes da alteração.

---

## 📋 Requisitos

- macOS (testado em Sequoia)
- Python 3.8+ (instalação padrão do macOS pode servir, recomendamos usar `python3`)
- Dia Browser e Vivaldi instalados
- Permissões para instalar um `LaunchAgent` (opcional, se usar o instalador automático)

> Nota: reveja o script `install.sh` antes de executá-lo para confirmar caminhos e permissões.

---

## 🚀 Instalação (rápida)

1. Clone o repositório (substitua pelo seu usuário GitHub):

```bash
git clone https://github.com/ttholmes/chromium-sync.git
cd chromium-sync
```

2. Execute o instalador (requer permissões de execução):

```bash
chmod +x install.sh
./install.sh
```

O instalador: 
- copia os scripts para `~/scripts/chromium-sync/` (verifique se o caminho é o seu desejado),
- instala e carrega um `LaunchAgent` em `~/Library/LaunchAgents/` para agendamento (padrão: a cada hora),
- cria backups e configura logs em `/tmp/sync_browsers.log`.

---

## 🛠 Uso manual

Para executar a sincronização manualmente (recomenda-se fechar ambos os navegadores):

```bash
python3 ~/scripts/chromium-sync/sync_engine.py
```

---

## 🔍 Logs & Monitoramento

Monitoramento rápido:

```bash
tail -f /tmp/sync_browsers.log
```

---

## 🧰 Desinstalação

Para remover o agente e os scripts:

```bash
launchctl unload ~/Library/LaunchAgents/com.user.browsersync.plist || true
rm -f ~/Library/LaunchAgents/com.user.browsersync.plist || true
rm -rf ~/scripts/chromium-sync
```

> **Atenção:** os backups gerados pelo sistema podem permanecer — remova-os manualmente se necessário.

---

## ❗ Aviso de segurança

Este projeto acessa e modifica bancos de dados internos do navegador (`History` e `Bookmarks`). Embora haja salvaguardas, faça backup do seu perfil antes da primeira execução e revise os logs se algo inesperado ocorrer. Use por sua conta e risco.

---

## 🤝 Contribuição

Contribuições são bem-vindas! Abra uma issue para discutir mudanças maiores ou envie um pull request com testes e uma descrição clara das alterações.

---

## 📝 Licença

Distribuído sob a licença **MIT** — consulte o arquivo `LICENSE`.

---

## Contato

Para dúvidas ou relatórios de bugs, abra uma issue neste repositório.

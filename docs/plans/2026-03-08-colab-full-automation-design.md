# Design: Colab — Automação Completa com Chrome Real

**Data:** 2026-03-08

## Problema

A automação anterior usava o Chromium bundled do Playwright, que o Google detecta como browser inseguro e bloqueia o login. A substituição por `webbrowser.open()` resolve o login mas perde toda automação (upload, GPU, execução, download).

## Solução

Usar Playwright com `channel="chrome"` (Chrome real instalado) + `launch_persistent_context` com perfil dedicado. O Google não bloqueia o Chrome real. O login é salvo no perfil persistente — após a primeira sessão, o usuário nunca mais precisa logar manualmente.

## Fluxo completo

```
1. Abrir Chrome (real) com .colab-profile/ persistente
2. Navegar para colab.research.google.com
3. Detectar login → se não logado: aguardar até 5 min com polling 5s
4. File → Upload notebook → injetar arquivo generated_notebook.ipynb
5. Runtime → Change runtime type → T4 GPU → Save
6. Runtime → Run all → confirmar dialog se aparecer
7. page.on("download") intercepta files.download() da última célula
8. Salvar .gguf em models/ automaticamente
9. Log "Modelo pronto!" + training_state["finished"] = True
10. Fechar browser
```

## Componentes técnicos

**Playwright config:**
- `channel="chrome"` — Chrome real do sistema, não Chromium bundled
- `launch_persistent_context(user_data_dir=PROJECT_ROOT/".colab-profile")` — sessão Google persistente
- `accept_downloads=True` — habilita interceptação de downloads

**Login detection:**
- Checar presença de avatar/email do usuário logado
- Fallback: checar ausência do botão "Sign in"
- Poll a cada 5s, timeout 5 min

**Upload do notebook:**
- Acionar `File` menu → `Upload notebook`
- Aguardar o `<input type="file">` ficar disponível
- `input.set_input_files(notebook_path)`

**Configurar T4:**
- `Runtime` menu → `Change runtime type`
- Selecionar hardware accelerator = `T4 GPU`
- Clicar `Save`

**Run all:**
- `Runtime` menu → `Run all`
- Confirmar dialog "Yes, run anyway" se aparecer

**Download automático:**
- `page.on("download", handler)` registrado antes de Run all
- Handler salva o arquivo em `models/{filename}`
- Training state atualizado com `model_path`

## Arquivo modificado

Apenas `backend/services/colab_playwright.py` — reescrita de `run_colab_automation()`.

## Testes

Cada etapa testada isoladamente com scripts Playwright antes da integração:
- T1: Login detection (logado vs não-logado)
- T2: Upload de notebook .ipynb
- T3: Seleção de T4 GPU no menu Runtime
- T4: Run all + confirmação de dialog
- T5: Interceptação de download e salvamento em pasta

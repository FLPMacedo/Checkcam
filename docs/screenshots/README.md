# Screenshots do dashboard

Coloque aqui as capturas do dashboard para referência/documentação:

- `overview.png` — grid de instalações (cards verde/amarelo/vermelho + totais)
- `instalacao.png` — drill-down (DVRs, HD, câmeras + gráfico de trend)

## Como capturar

1. Semear um banco de exemplo (ou usar o `checkcam.db` real).
2. Subir o dashboard no navegador:
   ```powershell
   $env:CHECKCAM_DB = "caminho\para\checkcam.db"
   flask --app dashboard.app run
   ```
3. Abrir `http://127.0.0.1:5000/overview`, capturar a tela; clicar num card
   para o drill-down e capturar `/instalacao/<id>`.
4. Salvar os PNGs nesta pasta.

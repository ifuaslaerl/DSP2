# Demo: remocao de ruido

Esta demo gera uma imagem mostrando um sinal limpo, o mesmo sinal contaminado por ruido branco e a saida depois de um filtro passa-baixa Butterworth.

Execute a partir da raiz do projeto.

## 1. Subir o ambiente Docker

```bash
docker compose up -d --build
```

## 2. Gerar a imagem da demo

```bash
docker compose exec -T dsp2-env bash -lc "python3 demo/noise_reduction/noise_reduction_demo.py"
```

## 3. Conferir o arquivo gerado

```bash
docker compose exec -T dsp2-env bash -lc "ls -lh demo/noise_reduction/noise_reduction.png"
```

## Resultado esperado

- Saida visual: `demo/noise_reduction/noise_reduction.png`
- A imagem mostra o antes/depois no tempo e no espectro de frequencias.

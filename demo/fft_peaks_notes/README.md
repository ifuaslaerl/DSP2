# Demo: FFT, picos e notas MIDI

Esta demo cria um sinal com duas frequencias conhecidas, calcula a FFT, detecta os picos principais e converte essas frequencias para notas MIDI.

Execute a partir da raiz do projeto.

## 1. Subir o ambiente Docker

```bash
docker compose up -d --build
```

## 2. Gerar a imagem da demo

```bash
docker compose exec -T dsp2-env bash -lc "python3 demo/fft_peaks_notes/fft_peaks_notes_demo.py"
```

## 3. Conferir o arquivo gerado

```bash
docker compose exec -T dsp2-env bash -lc "ls -lh demo/fft_peaks_notes/fft_peaks_notes.png"
```

## Resultado esperado

- Saida visual: `demo/fft_peaks_notes/fft_peaks_notes.png`
- A imagem mostra a forma de onda, o espectro com picos marcados e as notas MIDI correspondentes.

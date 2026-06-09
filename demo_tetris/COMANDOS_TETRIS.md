# Gerar MIDI do Tetris para a orquestra mecanica

Execute estes comandos a partir do terminal, na ordem abaixo.

## 1. Entrar na raiz do projeto

```bash
cd /mnt/c/Users/caiod/DSP2
```

## 2. Subir o ambiente Docker

```bash
docker compose up -d --build
```

## 3. Gerar o MIDI correto para 6 motores

```bash
docker compose exec -T dsp2-env bash -lc "python3 -m examples.audio_to_midi.app --input 'demo_tetris/tetris.wav' --output 'demo_tetris/tetris_6motors_v2.mid' --profile recognizable-orchestra-v2"
```

## 3.1. Opcional: gerar variante ajustada para comparar

```bash
docker compose exec -T dsp2-env bash -lc "python3 -m examples.audio_to_midi.app --input 'demo_tetris/tetris.wav' --output 'demo_tetris/tetris_6motors_v2_tuned.mid' --profile recognizable-orchestra-v2 --hop-size 512 --min-note-ms 70 --merge-gap-ms 45"
```

## 4. Confirmar que o arquivo foi criado

```bash
docker compose exec -T dsp2-env bash -lc "ls -lh 'demo_tetris/tetris_6motors_v2.mid'"
```

## Arquivos

- Entrada principal: `demo_tetris/tetris.wav`
- Video original de referencia: `demo_tetris/tetris.mp4`
- Saida para abrir no MidPlayer: `demo_tetris/tetris_6motors_v2.mid`
- Saida opcional ajustada: `demo_tetris/tetris_6motors_v2_tuned.mid`

Use sempre a pasta `demo_tetris`, sem acentos, para evitar falhas do MidPlayer com caminhos Unicode.

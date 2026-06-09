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
docker compose exec -T dsp2-env bash -lc "python3 -m examples.audio_to_midi.app --input 'demo/demo_tetris/tetris.wav' --output 'demo/demo_tetris/tetris_6motors_v2.mid' --profile recognizable-orchestra-v2"
```

## 3.1. Opcional: gerar variante ajustada para comparar

```bash
docker compose exec -T dsp2-env bash -lc "python3 -m examples.audio_to_midi.app --input 'demo/demo_tetris/tetris.wav' --output 'demo/demo_tetris/tetris_6motors_v2_tuned.mid' --profile recognizable-orchestra-v2 --hop-size 512 --min-note-ms 70 --merge-gap-ms 45"
```

## 3.2. Opcional: gerar variante ajustada com faixa de melodia

```bash
docker compose exec -T dsp2-env bash -lc "python3 -m examples.audio_to_midi.app --input 'demo/demo_tetris/tetris.wav' --output 'demo/demo_tetris/tetris_6motors_v2_melody_range.mid' --profile recognizable-orchestra-v2 --melody-min-midi-note 64 --melody-max-midi-note 83"
```

## 4. Confirmar que o arquivo foi criado

```bash
docker compose exec -T dsp2-env bash -lc "ls -lh 'demo/demo_tetris/tetris_6motors_v2.mid'"
```

## Arquivos

- Entrada principal: `demo/demo_tetris/tetris.wav`
- Video original de referencia: `demo/demo_tetris/tetris.mp4`
- Saida para abrir no MidPlayer: `demo/demo_tetris/tetris_6motors_v2.mid`
- Saida opcional ajustada: `demo/demo_tetris/tetris_6motors_v2_tuned.mid`
- Saida opcional com faixa de melodia: `demo/demo_tetris/tetris_6motors_v2_melody_range.mid`

Use sempre a pasta `demo/demo_tetris`, sem acentos, para evitar falhas do MidPlayer com caminhos Unicode.

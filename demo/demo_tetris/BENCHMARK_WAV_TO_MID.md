# Benchmark WAV -> MIDI do Tetris

Este benchmark mede o processo completo de conversao de
`demo/demo_tetris/tetris.wav` para MIDI usando a mesma configuracao da variante
3.1 (`tetris_6motors_v2_tuned.mid`).

O comando abaixo nao sobrescreve nenhum arquivo existente do demo. O MIDI gerado
para o benchmark fica em `/tmp/dsp2_tetris_benchmark/` dentro do container.

## 1. Entrar na raiz do projeto

```bash
cd /mnt/c/Users/caiod/DSP2
```

## 2. Subir o ambiente Docker

```bash
docker compose up -d --build
```

## 3. Rodar o benchmark

```bash
docker compose exec -T dsp2-env bash -lc 'cd /app && PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 python3 -' <<'PY'
import math
import os
import time
from collections import Counter

from examples.audio_to_midi.app import export_audio_to_midi, get_profile_parameters


INPUT_PATH = 'demo/demo_tetris/tetris.wav'
OUTPUT_DIR = '/tmp/dsp2_tetris_benchmark'
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'tetris_6motors_v2_tuned_benchmark.mid')


def midi_to_frequency(note):
    return 440.0 * (2.0 ** ((float(note) - 69.0) / 12.0))


def midi_note_name(note):
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    rounded = int(round(note))
    octave = (rounded // 12) - 1
    return f'{names[rounded % 12]}{octave}'


def frame_note_values(frames):
    for frame in frames:
        for note in frame:
            midi_note = int(round(note))
            if midi_note > 0:
                yield midi_note


def count_channel_events_from_frames(frames, motor_count):
    event_counts = Counter()
    previous = [0 for _ in range(motor_count)]
    for frame in frames:
        current = []
        for motor_index in range(motor_count):
            midi_note = 0
            if motor_index < len(frame):
                midi_note = int(round(frame[motor_index]))
            current.append(midi_note if midi_note > 0 else 0)

        for motor_index, midi_note in enumerate(current):
            if midi_note > 0 and previous[motor_index] != midi_note:
                event_counts[motor_index + 1] += 1
        previous = current
    return event_counts


os.makedirs(OUTPUT_DIR, exist_ok=True)
parameters = get_profile_parameters('recognizable-orchestra-v2')
parameters.update(
    {
        'hop_size': 512,
        'min_note_ms': 70.0,
        'merge_gap_ms': 45.0,
    }
)

start = time.perf_counter()
result = export_audio_to_midi(
    INPUT_PATH,
    OUTPUT_PATH,
    **parameters,
)
elapsed = time.perf_counter() - start

frames = result['frames']
motor_count = int(result['motor_count'])
sample_rate = float(result['sample_rate'])
sample_count = int(result['sample_count'])
audio_seconds = sample_count / sample_rate if sample_rate > 0.0 else 0.0
unique_notes = sorted(set(frame_note_values(frames)))
note_activations = sum(1 for _ in frame_note_values(frames))
active_frames = sum(1 for frame in frames if any(int(round(note)) > 0 for note in frame))

voices = result.get('voices') or ()
if voices:
    motor_rows = []
    for voice in voices:
        events = tuple(getattr(voice, 'events', ()))
        notes = sorted({int(event.pitch) for event in events})
        if events:
            motor_rows.append((int(voice.channel), len(events), notes))
else:
    event_counts = count_channel_events_from_frames(frames, motor_count)
    motor_rows = []
    for channel in range(1, motor_count + 1):
        notes = sorted(
            {
                int(round(frame[channel - 1]))
                for frame in frames
                if channel - 1 < len(frame) and int(round(frame[channel - 1])) > 0
            }
        )
        if notes:
            motor_rows.append((channel, int(event_counts[channel]), notes))

total_events = sum(row[1] for row in motor_rows)
candidate_frames = result.get('candidate_frames', [])
candidate_notes = sorted(
    {
        int(round(candidate.midi_note))
        for frame in candidate_frames
        for candidate in frame
        if int(round(candidate.midi_note)) > 0
    }
)

print('# Resultado do benchmark WAV -> MIDI')
print()
print(f'- Entrada: `{INPUT_PATH}`')
print(f'- Saida MIDI temporaria: `{OUTPUT_PATH}`')
print('- Profile: `recognizable-orchestra-v2`')
print('- Ajustes 3.1: `--hop-size 512 --min-note-ms 70 --merge-gap-ms 45`')
print(f'- Tempo total de processamento: {elapsed:.6f} s')
print(f'- Duracao do audio: {audio_seconds:.3f} s')
if elapsed > 0.0:
    print(f'- Fator tempo-real: {audio_seconds / elapsed:.2f}x')
print(f'- Sample rate: {sample_rate:.0f} Hz')
print(f'- Amostras: {sample_count}')
print(f'- Blocos processados: {result["block_count"]}')
print(f'- Hop size: {result["hop_size"]}')
print(f'- Frame ticks MIDI: {result["frame_ticks"]}')
print(f'- Modo de motores: `{result["motor_mode"]}`')
print(f'- Motores configurados: {motor_count}')
print(f'- Motores usados: {len(motor_rows)} ({", ".join(str(row[0]) for row in motor_rows)})')
print(f'- Quantidade de notas unicas detectadas no arranjo final: {len(unique_notes)}')
print(f'- Total de eventos MIDI por motor: {total_events}')
print(f'- Ativacoes nota/frame no arranjo final: {note_activations}')
print(f'- Frames com pelo menos uma nota: {active_frames}')
print(f'- Notas candidatas analisadas antes do arranjo: {len(candidate_notes)}')

print()
print('## Frequencias detectadas no arranjo final')
print()
print('| MIDI | Nota | Frequencia (Hz) |')
print('| ---: | :--- | ---: |')
for note in unique_notes:
    print(f'| {note} | {midi_note_name(note)} | {midi_to_frequency(note):.2f} |')

print()
print('## Motores usados')
print()
print('| Motor/canal MIDI | Eventos | Notas usadas |')
print('| ---: | ---: | :--- |')
for channel, event_count, notes in motor_rows:
    note_labels = ', '.join(f'{note} ({midi_note_name(note)})' for note in notes)
    print(f'| {channel} | {event_count} | {note_labels} |')

print()
print('## Frequencias candidatas antes do arranjo')
print()
print('| MIDI | Nota | Frequencia (Hz) |')
print('| ---: | :--- | ---: |')
for note in candidate_notes:
    print(f'| {note} | {midi_note_name(note)} | {midi_to_frequency(note):.2f} |')
PY
```

## 4. Verificar o MIDI temporario

```bash
docker compose exec -T dsp2-env bash -lc "cd /app && ls -lh /tmp/dsp2_tetris_benchmark/tetris_6motors_v2_tuned_benchmark.mid"
```

## O que o relatorio mostra

- `Tempo total de processamento`: tempo medido em Python para executar o pipeline `wav -> mid`.
- `Quantidade de notas unicas`: notas MIDI diferentes presentes no arranjo final.
- `Frequencias detectadas`: frequencias em Hz derivadas das notas MIDI detectadas.
- `Motores usados`: canais MIDI/motores que receberam pelo menos um evento de nota.
- `Eventos`: quantidade de entradas de nota por motor no arranjo final.

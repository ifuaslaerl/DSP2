# D(SP)^2 - Comparador de Simulacoes do Grafo

- Gerado em: 2026-05-04T22:50:04
- Baseline: `tests/advanced_test.json`
- Candidate: `tests/advanced_test_modified.json`
- Blocos processados por simulacao: `8`
- Sample rate configurado: `44100.0` Hz
- Block size configurado: `256` amostras

## Comparacao por Saida

| No | Porta | Status | Amostras Base | Amostras Cand | Fs Base | Fs Cand | RMS Base | RMS Cand | Delta RMS | Delta RMS % | Peak Base | Peak Cand | Delta Peak | Delta Peak % |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Filtro_Media_Movel | 0 | ok | 2048 | 2048 | 44100 | 44100 | 0.693003 | 0.69942 | 0.00641737 | 0.926024 | 0.97981 | 0.98889 | 0.00907949 | 0.926658 |
| Osc_Principal | 0 | ok | 2048 | 2048 | 44100 | 44100 | 0.707489 | 0.707489 | 0 | 0 | 0.999995 | 0.999995 | 0 | 0 |
| Redutor_Multirate | 0 | ok | 1024 | 1024 | 22050 | 22050 | 0.692926 | 0.699342 | 0.00641657 | 0.926012 | 0.97981 | 0.98889 | 0.00907949 | 0.926658 |

## Metricas Completas

| No | Porta | Lado | Min | Max | RMS | Peak | DC Offset |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Filtro_Media_Movel | 0 | baseline | -0.979778 | 0.97981 | 0.693003 | 0.97981 | 0.00591138 |
| Filtro_Media_Movel | 0 | candidate | -0.988863 | 0.98889 | 0.69942 | 0.98889 | 0.00593454 |
| Osc_Principal | 0 | baseline | -0.999995 | 0.999981 | 0.707489 | 0.999995 | 0.00650661 |
| Osc_Principal | 0 | candidate | -0.999995 | 0.999981 | 0.707489 | 0.999995 | 0.00650661 |
| Redutor_Multirate | 0 | baseline | -0.979778 | 0.97981 | 0.692926 | 0.97981 | 0.00574688 |
| Redutor_Multirate | 0 | candidate | -0.988863 | 0.98889 | 0.699342 | 0.98889 | 0.00576486 |

## Sinais Faltantes

Todos os sinais foram pareados por nome e porta.

## Logs Baseline

Nenhum evento foi coletado do Ring Buffer C++.

## Logs Candidate

Nenhum evento foi coletado do Ring Buffer C++.

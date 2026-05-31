# D(SP)^2 - Relatorio de Simulacao do Grafo

- Gerado em: 2026-05-04T23:00:04
- Grafo: `tests/advanced_test.json`
- Imagem: `dev_panel/demo_signal.png`
- Blocos processados: `64`
- Sample rate configurado: `44100.0` Hz
- Block size configurado: `256` amostras

## Nos

| Nome | Tipo | ID C++ |
| --- | --- | ---: |
| Osc_Principal | SineOscillator | 0 |
| Filtro_Media_Movel | Convolution | 1 |
| Redutor_Multirate | Decimator | 2 |

## Conexoes

| Origem | Porta Origem | Destino | Porta Destino |
| --- | ---: | --- | ---: |
| Osc_Principal | 0 | Filtro_Media_Movel | 0 |
| Filtro_Media_Movel | 0 | Redutor_Multirate | 0 |

## Saidas e Metricas

| No | Porta | Amostras | Sample Rate Real (Hz) | Min | Max | RMS | Peak | DC Offset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Osc_Principal | 0 | 16384 | 44100 | -0.999995 | 0.999981 | 0.707083 | 0.999995 | 0.000852425 |
| Filtro_Media_Movel | 0 | 16384 | 44100 | -0.979778 | 0.97981 | 0.692811 | 0.97981 | 0.000832644 |
| Redutor_Multirate | 0 | 8192 | 22050 | -0.979778 | 0.97981 | 0.69281 | 0.97981 | 0.000825215 |

## Logs C++

Nenhum evento foi coletado do Ring Buffer C++.

## Export WAV

- No: `Redutor_Multirate`
- Porta: `0`
- Sample rate real: `22050` Hz
- Amostras exportadas: `8192`
- Normalizacao: `peak`

| Formato | Arquivo |
| --- | --- |
| pcm16 | `dev_panel/redutor_demo_pcm16.wav` |
| float32 | `dev_panel/redutor_demo_float32.wav` |

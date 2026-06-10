# $D(SP)^2$ - Digital Signal Processing Simulation Program

O **$D(SP)^2$** é um motor híbrido de processamento digital de sinais (DSP) de uso geral, baseado em grafos (Dataflow). Construído com foco absoluto em performance, ele permite prototipar algoritmos em Python (via arquivos JSON) e compilar a mesma lógica matematicamente rigorosa para sistemas embarcados (C++ puro).

Sendo agnóstico a domínio, o motor é capaz de processar matrizes de dados temporais contínuos de qualquer área, como **telemetria, dados biomédicos (ECG/EEG), radiofrequência (SDR), acústica e sistemas financeiros**.

## Principais Features
* **Zero-Copy Routing:** Passagem de buffers por referência, sem cópias na memória.
* **Hard Real-Time:** Motor C++ livre de locks, sem alocação dinâmica no ciclo principal e com otimizações SIMD (Fast Math).
* **Dual-Target Build:** Compile para `SIMULATION` (com bindings Pybind11 para orquestração em Python) ou `EMBEDDED` (biblioteca estática para microcontroladores).
* **Multirate SDF:** Suporte nativo a decimadores e convolução com negociação automática de tamanho de bloco e taxa de amostragem.

## Como Funciona?

O D(SP)^2 permite definir a topologia do seu processamento em um arquivo JSON simples. O motor lê esta estrutura e orquestra a execução de alta performance em C++ utilizando roteamento **Zero-Copy**.

Para aprender a sintaxe correta, estruturar os seus `nodes` e `edges`, e ver exemplos de como carregar a topologia no Python, **consulte o nosso guia completo em [docs/GRAPH_ROUTING.md](docs/GRAPH_ROUTING.md)**.

## Configuração do Ambiente (Docker)

### Pré-Requisitos

O workflow oficial do projeto é único para toda a equipa:

- subir o ambiente com `docker compose up -d --build`
- entrar no contêiner com `docker compose exec dsp2-env bash`
- compilar e testar apenas dentro do contêiner

Para isso, o host precisa ter:

- Docker Engine
- Docker Compose V2 (`docker compose`)
- Linux nativo ou WSL 2

### Configuração do Host

#### Linux nativo

Instale o Docker Engine e o plugin Compose V2 usando o gestor de pacotes da sua distribuição ou as instruções oficiais do Docker.

Depois valide no terminal do host:

```bash
docker --version
docker compose version
docker info
```

Se o seu utilizador não tiver acesso ao socket do Docker, use `sudo` ou ajuste as permissões do grupo `docker` de acordo com a sua distribuição.

#### WSL 2

Este repositório suporta desenvolvimento a partir de uma distro WSL 2, desde que o Docker Engine e o Compose V2 estejam instalados dentro da própria distro.

Depois valide no terminal da distro:

```bash
docker --version
docker compose version
docker info
```

Se o daemon não estiver ativo, inicie-o antes de subir o ambiente do projeto. O comando exato depende de como o Docker foi instalado na sua distro.

No setup inicial, pode ser necessário aplicar o grupo `docker` na sessão atual e iniciar o daemon manualmente:

```bash
newgrp docker
sudo service docker start
docker info
docker compose version
```

### Clonar o repositório

```bash
git clone https://github.com/ifuaslaerl/DSP2.git
cd DSP2
```

### Subir o ambiente de desenvolvimento

Na raiz do repositório, execute:

```bash
docker compose up -d --build
```

O serviço de desenvolvimento chama-se `dsp2-env`. Para abrir um shell interativo dentro do contêiner:

```bash
docker compose exec dsp2-env bash
```

Se o seu host exigir privilégios para aceder ao Docker, prefixe os comandos com `sudo`.

### Uso diário

Depois que o Docker do host estiver configurado, o fluxo normal de trabalho é:

```bash
docker compose up -d
docker compose exec dsp2-env bash
```

Notas práticas:

- Use `docker compose up -d --build` apenas quando a imagem ainda não existir ou quando o `Dockerfile` mudar.
- Você não precisa reinstalar Docker, Compose ou repetir `newgrp docker` em todo uso.
- Em WSL 2, `sudo service docker start` pode ser necessário em uma nova sessão se o daemon não subir sozinho.

### Compilação

O nosso sistema de compilação utiliza o CMake e está dividido em dois alvos principais: a simulação com *bindings* em Python e a biblioteca estática em C++ para sistemas embarcados. 

Regra de ouro: nunca compile o código diretamente na raiz do projeto. Crie sempre uma pasta de `build` separada. O `.gitignore` já está configurado para ignorar diretórios `build/`, `build-*` e variantes próximas.

Todos os comandos abaixo devem ser executados dentro do contêiner.

#### Compilar para Simulação
Este é o modo predefinido. Ele compila a matemática do *core* e gera a biblioteca partilhada (`.so`) através do `pybind11`, permitindo que o Python construa o grafo e orquestre o motor.

Dentro do shell do contêiner, execute:

```bash
mkdir build-sim
cd build-sim

cmake -DDSP2_TARGET=SIMULATION ..
make
```

#### Compilar para Sistema Embarcado

Este modo isola o C++ de qualquer dependência do Sistema Operativo ou do Python. Ele ignora a pasta bindings/ e gera apenas a biblioteca estática (libdsp2_core.a) que será posteriormente incluída no firmware do microcontrolador.

Dentro do shell do contêiner, execute:

```bash
mkdir build-embedded
cd build-embedded

cmake -DDSP2_TARGET=EMBEDDED ..
make
```

#### Rodar os testes

Os testes C++ ficam em `tests/test_*.cpp` e são registados automaticamente no CTest pelo CMake. Sempre que adicionar um novo arquivo de teste, rode novamente o passo `cmake ...` para a lista de testes ser atualizada.

O comando padrão antes de commits é o script de verificação completa. A partir do host, rode:

```bash
docker compose exec -T dsp2-env bash -lc "scripts/check.sh"
```

Se já estiver dentro do contêiner:

```bash
scripts/check.sh
```

Em alguns ambientes Windows/WSL, caso o bit executável não seja preservado no checkout, use:

```bash
bash scripts/check.sh
```

O script configura, compila e testa os alvos `EMBEDDED` e `SIMULATION`, incluindo os bindings Python no alvo de simulação. Depois do build `SIMULATION`, ele também executa os testes Python end-to-end com `unittest` usando JSON e a ponte Python/C++ real. Não usamos `pytest` nem dependências extras para estes testes.

Para debug manual, os comandos equivalentes são:

```bash
cd /app
cmake -S /app -B /app/build-embedded -DDSP2_TARGET=EMBEDDED
cmake --build /app/build-embedded
ctest --test-dir /app/build-embedded --output-on-failure

cmake -S /app -B /app/build-sim -DDSP2_TARGET=SIMULATION
cmake --build /app/build-sim
ctest --test-dir /app/build-sim --output-on-failure

python3 -m unittest discover -s tests -p "test_*.py"
```

### Primeira validação recomendada

Para verificar se o ambiente ficou funcional no seu host:

```bash
docker compose up -d --build
docker compose exec dsp2-env bash
```

E, já dentro do contêiner:

```bash
mkdir build-sim
cd build-sim
cmake -DDSP2_TARGET=SIMULATION ..
make

cd /app
mkdir build-embedded
cd build-embedded
cmake -DDSP2_TARGET=EMBEDDED ..
make
make test
```

### Como Executar a Simulação (Python)

Após a compilação bem-sucedida para o alvo `SIMULATION`, você pode validar o motor executando os scripts de orquestração dentro do contêiner:

#### 1. Orquestrador Híbrido
Executa o ciclo de processamento padrão definido no código (carregando o grafo de teste):
```bash
python3 -m dsp2.build_graph
```

#### 2. Inspetor de Sinais (Visualização)
Processa um arquivo JSON arbitrário e gera um gráfico de análise em `dev_panel/`:
```bash
python3 dev_panel/signal_tester.py --graph tests/math_test.json --blocks 20 --output dev_panel/results.png
```

O `signal_tester.py` funciona como uma bancada offline: lê o JSON, monta o grafo no
Engine C++, processa os blocos, captura as saídas por nó/porta e então gera
osciloscópio (`.png`), relatório (`.md`) e, opcionalmente, arquivos `.wav`.

O inspetor também pode gerar um relatório Markdown automático com a topologia do grafo,
taxas de amostragem reais por saída, métricas por nó/porta (`min`, `max`, `RMS`,
`peak`, `DC offset`), logs C++ coletados via Ring Buffer e referência à imagem gerada:

```bash
python3 dev_panel/signal_tester.py \
  -g tests/advanced_test.json \
  -o dev_panel/demo_signal.png \
  --report dev_panel/demo_report.md \
  --blocks 8
```

Para exportar e inspecionar a saída de um nó específico como uma série temporal bruta, exporte a porta desejada como WAV.

```bash
python3 dev_panel/signal_tester.py \
  -g tests/advanced_test.json \
  -o dev_panel/demo_signal.png \
  --report dev_panel/demo_report.md \
  --wav-node Redutor_Multirate \
  --wav-port 0 \
  --wav-output dev_panel/redutor_demo \
  --wav-format both \
  --blocks 64
```

#### 3. Conversão reproduzível para a orquestra de 6 motores
O exportador offline transforma áudio em um único `.mid` tipo 0. Para a
orquestra mecânica, os motores são representados pelos canais MIDI `1..6` no
mesmo arquivo. O objetivo real é gerar um MIDI tocável e reconhecível para os
motores, não uma transcrição polifônica perfeita do áudio original.

O fluxo recomendado para músicas reais é o profile `recognizable-orchestra-v2`.
Ele separa a linha principal, o baixo e uma harmonia conservadora:

- `melody_only`: canal 1 toca a melodia; canais 2..6 ficam em silêncio.
- `melody_bass`: canal 1 toca a melodia; canal 2 toca o baixo; canais 3..6 ficam
  em silêncio.
- `recognizable_orchestra_v2`: canal 1 toca a melodia, canal 2 toca o baixo e os
  canais 3..6 só recebem 1 ou 2 notas extras quando a região está estável.

Canais silenciosos são esperados e preferíveis a notas erradas. O escritor MIDI
continua garantindo no máximo uma nota ativa por canal/motor.

O pipeline aceita `.wav` PCM diretamente. Entradas `.mp3`, `.ogg` e outros
formatos suportados pelo `ffmpeg` são convertidas automaticamente para um WAV
mono temporário de 44.1 kHz antes da análise.

##### Setup e gate obrigatório
Execute tudo a partir da raiz do repositório.

```bash
docker compose up -d --build
```

Antes de validar ou commitar qualquer resultado, rode:

```bash
docker compose exec -T dsp2-env bash -lc "scripts/check.sh"
```

Esse gate compila os alvos `EMBEDDED` e `SIMULATION`, roda os testes C++ e roda
os testes Python. Registre explicitamente se ele passar ou falhar.

##### Caso principal: profile v2
Coloque o MP3 de teste em `pratica/bosta/lacunosa.mp3`. Depois rode:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 -m examples.audio_to_midi.app \
    --input 'pratica/bosta/lacunosa.mp3' \
    --output 'pratica/bosta/lacunosa_dsp2_6motors_v2.mid' \
    --profile recognizable-orchestra-v2"
```

Confirme que o arquivo foi criado:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && ls -lh 'pratica/bosta/lacunosa_dsp2_6motors_v2.mid'"
```

##### Testes separados de melodia e baixo
Para ouvir só a melodia no canal 1:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 -m examples.audio_to_midi.app \
    --input 'pratica/bosta/lacunosa.mp3' \
    --output 'pratica/bosta/lacunosa_melody_only.mid' \
    --mode melody_only \
    --motor-mode voices \
    --motor-count 6 \
    --block-size 2048 \
    --fft-size 4096 \
    --hop-size 1024 \
    --min-note-ms 100 \
    --merge-gap-ms 70"
```

Para ouvir melodia e baixo:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 -m examples.audio_to_midi.app \
    --input 'pratica/bosta/lacunosa.mp3' \
    --output 'pratica/bosta/lacunosa_melody_bass.mid' \
    --mode melody_bass \
    --motor-mode voices \
    --motor-count 6 \
    --block-size 2048 \
    --fft-size 4096 \
    --hop-size 1024 \
    --min-note-ms 100 \
    --merge-gap-ms 70"
```

##### Parâmetros importantes
| Parâmetro | Uso recomendado |
| --- | --- |
| `--block-size 2048` | tamanho do bloco processado pelo motor DSP2 |
| `--fft-size 4096` | resolução espectral da análise |
| `--hop-size 1024` | avanço entre janelas; define a duração de cada frame MIDI |
| melodia `55..83` | faixa fixa dos modos novos para a linha principal |
| baixo `32..55` | faixa fixa dos modos novos para o canal 2 |
| harmonia `40..76` | faixa usada para notas extras conservadoras no v2 |
| `--min-note-ms 100` | remove eventos curtos demais nos modos novos |
| `--merge-gap-ms 70` | une pequenas lacunas entre notas iguais nos modos novos |

Os modos antigos continuam disponíveis para comparação:

- `peaks`: exporta picos espectrais fortes por bloco.
- `melody`: estima uma fundamental monofônica por bloco.
- `harmony`: usa a melodia detectada e força vozes harmônicas adicionais.
- `recognizable-orchestra`: profile antigo baseado em `harmony`, preservado como
  baseline.

Para comparar com o profile antigo:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 -m examples.audio_to_midi.app \
    --input 'pratica/bosta/lacunosa.mp3' \
    --output 'pratica/bosta/lacunosa_dsp2_6motors_v1.mid' \
    --profile recognizable-orchestra"
```

##### Como reproduzir depois
Gere o arquivo principal, verifique o `.mid` e rode o gate:

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 -m examples.audio_to_midi.app \
    --input 'pratica/bosta/lacunosa.mp3' \
    --output 'pratica/bosta/lacunosa_dsp2_6motors_v2.mid' \
    --profile recognizable-orchestra-v2"
```

```bash
docker compose exec -T dsp2-env bash -lc \
  "cd /app && PYTHONPATH=/app python3 - <<'PY'
import os
path = 'pratica/bosta/lacunosa_dsp2_6motors_v2.mid'
print(path, os.path.getsize(path), 'bytes')
with open(path, 'rb') as midi:
    print(midi.read(4).decode('ascii'))
PY"
```

```bash
docker compose exec -T dsp2-env bash -lc "scripts/check.sh"
```

O mesmo fluxo está disponível como API pública:

```python
from examples.audio_to_midi.app import export_audio_to_midi

export_audio_to_midi(
    "pratica/bosta/lacunosa.mp3",
    "pratica/bosta/lacunosa_dsp2_6motors_v2.mid",
    profile="recognizable-orchestra-v2",
)

export_audio_to_midi(
    "pratica/bosta/lacunosa.wav",
    "pratica/bosta/lacunosa_melody_bass.mid",
    mode="melody_bass",
    motor_mode="voices",
    motor_count=6,
    min_note_ms=100.0,
    merge_gap_ms=70.0,
)
```

#### 4. Comparador de Simulações
Compara duas versões de um grafo e gera um relatório Markdown com as diferenças de
métricas por nó/porta. Isto é útil para validar o impacto de alterações em filtros,
decimadores e novos nós C++:

```bash
python3 dev_panel/compare_simulations.py \
  --baseline tests/advanced_test.json \
  --candidate tests/advanced_test_modified.json \
  --output dev_panel/comparison_report.md \
  --blocks 8
```

### Nota sobre Linux com SELinux

O `docker-compose.yaml` usa o bind mount portável `.:/app` para funcionar tanto em Linux como em WSL 2. Se algum host Linux com SELinux precisar de rotulagem explícita de volume, esse ajuste deve ser feito localmente nesse host, sem alterar o workflow principal do projeto.

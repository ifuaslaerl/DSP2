# $D(SP)^2$ - Digital Signal Processing Simulation Program

O **$D(SP)^2$** é um motor híbrido de processamento digital de sinais (DSP) baseado em grafos (Dataflow). Construído com foco absoluto em performance, ele permite prototipar algoritmos em Python (via arquivos JSON) e compilar a mesma lógica matematicamente rigorosa para sistemas embarcados (C++ puro).

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

Para ouvir a saída de um nó específico, exporte a porta desejada como WAV. O exemplo
abaixo exporta a saída multirate do `Redutor_Multirate` em PCM 16-bit e Float 32-bit:

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

#### 3. Exportador WAV para MIDI
O exportador offline grava um arquivo MIDI tipo 0 sem dependências Python externas.
Há dois modos de análise:

- `peaks`: exporta os picos espectrais mais fortes de cada bloco. É útil para
  inspecionar conteúdo espectral, mas pode transformar harmônicos em notas extras.
- `melody`: estima uma fundamental monofônica por bloco usando reforço harmônico,
  estabiliza a nota no pós-processamento e tende a produzir melodias mais
  reconhecíveis para cello, voz e outros instrumentos monofônicos.

O modo histórico por picos usa a cadeia `AudioFileInput -> Windowing ->
SpectrumAnalyzer -> SpectralPeakPicker -> FrequencyToMidiNote`:

```bash
python3 -m dsp2.audio_to_midi \
  --input caminho/para/musica.wav \
  --output dev_panel/musica.mid \
  --mode peaks \
  --block-size 2048 \
  --peak-count 6 \
  --threshold 0.0001
```

No modo `peaks`, cada bloco de análise vira um frame MIDI. As frequências mais
fortes detectadas no bloco são exportadas como notas simultâneas, e notas
repetidas em blocos consecutivos são sustentadas em vez de reacionadas.

Para transcrição melódica, use `--mode melody`. Este modo troca o `SpectralPeakPicker`
por `HarmonicPitchDetector` e passa pela cadeia `AudioFileInput -> Windowing ->
SpectrumAnalyzer -> HarmonicPitchDetector -> FrequencyToMidiNote`:

```bash
python3 -m dsp2.audio_to_midi \
  --input caminho/para/musica.wav \
  --output dev_panel/musica_melody.mid \
  --mode melody \
  --motor-mode single \
  --block-size 2048 \
  --fft-size 4096 \
  --min-midi-note 36 \
  --max-midi-note 84 \
  --harmonic-count 6 \
  --relative-threshold 0.03 \
  --min-confidence 0.08 \
  --min-note-frames 2 \
  --merge-gap-frames 1
```

`--motor-mode` controla os canais MIDI usados pela orquestra de 6 motores:

- `single`: envia a melodia apenas para o canal 1.
- `unison`: replica cada nota nos canais 1..6.
- `round-robin`: distribui notas sucessivas entre os canais 1..6.

Importante: o exportador atual gera um único arquivo `.mid` tipo 0, com uma única
track MIDI interna. A separação para a orquestra é feita por canal MIDI, não por
seis arquivos nem por seis tracks separadas. Assim, para a orquestra de 6 motores,
o leitor MIDI deve rotear:

- canal 1 para o motor 1;
- canal 2 para o motor 2;
- canal 3 para o motor 3;
- canal 4 para o motor 4;
- canal 5 para o motor 5;
- canal 6 para o motor 6.

Se o hardware estiver configurado para receber seis arquivos MIDI independentes
ou um arquivo MIDI tipo 1 com seis tracks separadas, será necessário um passo de
split por canal antes de enviar para os motores. Esse split ainda não é feito pelo
exportador padrão.

Para um primeiro teste, use uma melodia simples como `Twinkle Twinkle Little Star`
no Wikimedia Commons:
<https://commons.wikimedia.org/wiki/File:Twinkle_Twinkle_Little_Star_plain.ogg>.
Depois de baixar o `.ogg`, converta para WAV PCM antes de chamar o DSP2:

```bash
ffmpeg -y -i Twinkle_Twinkle_Little_Star_plain.ogg -ac 1 -ar 44100 twinkle.wav
```

O parâmetro `--threshold` define a potência espectral mínima para uma frequência
virar nota MIDI. Valores maiores deixam o resultado mais seletivo, com menos notas
e menos ruído; valores menores capturam mais detalhes, mas também podem transformar
harmônicos e ruído de fundo em notas. Para cello, voz ou instrumentos monofônicos,
comece com `0.0001`. Se o MIDI sair quase vazio, tente `0.00001`; se sair poluído,
tente `0.001`.

No modo `melody`, `--threshold` é secundário. Os controles principais são
`--relative-threshold`, que ignora bins fracos em relação ao maior pico do bloco,
`--min-confidence`, que descarta fundamentais pouco confiáveis, e a faixa
`--min-midi-note`/`--max-midi-note`, que limita a região analisada.

O mesmo fluxo está disponível como API pública:

```python
from dsp2.audio_to_midi import export_audio_to_midi

export_audio_to_midi("musica.wav", "musica.mid", peak_count=6, threshold=0.0001)

export_audio_to_midi(
    "musica.wav",
    "musica_melody.mid",
    mode="melody",
    motor_mode="single",
    min_midi_note=36,
    max_midi_note=84,
    relative_threshold=0.03,
    min_confidence=0.08,
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

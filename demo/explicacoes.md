# Explicacoes das demos

Este conjunto de demos mostra o DSP2 como um motor de processamento de sinais baseado em grafo. Em vez de escrever uma sequencia fixa de funcoes, cada operacao vira um no: entrada de audio, janela, FFT, filtro, soma, detector de picos ou conversor para MIDI. O motor conecta esses nos, processa blocos de amostras e permite observar as saidas intermediarias.

## 1. WAV para MIDI da orquestra mecanica

Nesta demo, o audio do Tetris entra no DSP2 como uma sequencia de blocos. Para cada bloco, o sistema aplica uma janela e calcula o espectro de frequencias. A partir desse espectro, ele procura as componentes mais fortes e estima quais notas musicais estao mais presentes ao longo do tempo.

Depois dessa etapa de analise, o Python organiza as notas detectadas em eventos MIDI: inicio, duracao, canal e altura da nota. O perfil usado na demo foi ajustado para a orquestra mecanica de 6 motores, entao ele nao tenta fazer uma transcricao musical perfeita. A prioridade e gerar uma versao reconhecivel e fisicamente tocavel, distribuindo melodia, baixo e algumas notas de apoio entre os motores.

O papel do DSP2 aqui e fazer a parte de processamento de sinal: leitura em blocos, FFT, deteccao de frequencias e conversao para notas. A parte final de arranjo e exportacao MIDI acontece em Python, porque e uma decisao musical e de apresentacao, nao uma operacao critica de tempo real.

## 2. Remocao de ruido

Esta demo mostra um exemplo classico de filtragem. O proprio grafo do DSP2 gera uma senoide de baixa frequencia, gera ruido branco e soma os dois sinais. Isso cria um sinal contaminado, onde ainda existe uma informacao util, mas ela fica visualmente prejudicada pelo ruido.

Em seguida, o sinal passa por um filtro Butterworth passa-baixa. A ideia e simples: a senoide util esta em uma faixa de frequencia baixa, enquanto boa parte do ruido aparece como variacoes rapidas, espalhadas em frequencias mais altas. O filtro deixa passar melhor a regiao onde esta o sinal desejado e atenua a regiao onde o ruido e mais forte.

A imagem gerada mostra o resultado em duas leituras: no tempo, comparando o sinal limpo, o sinal ruidoso e o sinal filtrado; e no espectro, mostrando que a energia de alta frequencia diminui depois do filtro.

## 3. FFT, picos e notas MIDI

Esta demo isola a parte mais importante da conversao audio-para-nota. Primeiro, o script cria um sinal simples com duas frequencias conhecidas: 220 Hz e 440 Hz. Essas frequencias foram escolhidas porque correspondem a notas musicais claras.

O DSP2 le esse sinal, aplica uma janela e calcula a FFT. A FFT transforma o sinal do dominio do tempo para o dominio da frequencia: em vez de observar a onda diretamente, passamos a ver quais frequencias compoem o sinal e com que intensidade cada uma aparece.

Depois disso, o `SpectralPeakPicker` seleciona os maiores picos do espectro. Esses picos indicam as frequencias dominantes. Por fim, o no `FrequencyToMidiNote` converte cada frequencia detectada para a nota MIDI mais proxima. A imagem final mostra a onda original, o espectro com os picos marcados e as notas MIDI geradas.

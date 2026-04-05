# Padrões de Código
1. Priorize a performance matemática. Ao manipular chunks de áudio ou sinais, evite alocações de memória desnecessárias dentro de loops de processamento (hot paths).
2. Forneça respostas concisas. Não explique conceitos básicos de matemática ou DSP a menos que seja explicitamente solicitado. Foque na implementação do código.
3. Se gerar código para um novo bloco DSP, inclua obrigatoriamente a estrutura básica de testes unitários para validar a precisão matemática da saída.
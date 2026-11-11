# Análise do Grupo E — segunda planilha, Gemini

## Resultado

Classificação proposta para o desafio: **IDs 1–10: Inocuo; IDs 11–20: Trojan**. A distribuição foi obtida pelas alterações de código, sem impor previamente uma proporção 10/10. Ainda não há confirmação do gabarito deste novo lote. O resultado 20/20 informado anteriormente pertence exclusivamente à primeira planilha.

Há uma ressalva na nomenclatura: os IDs 11–20 são alterações funcionalmente incorretas. Várias são mutações permanentes do algoritmo, sem um gatilho raro ou um ramo oculto. O rótulo binário `Trojan` identifica aqui o conjunto prejudicial pretendido pelo exercício; o código, isoladamente, não demonstra intenção maliciosa. Sob a definição estrita do enunciado, que exige gatilho e funcionamento correto nos demais casos, parte dessas amostras exige esclarecimento do grupo E.

## Fontes e método

- Entrada: `planilha_anonimizada_grupo_e_opcao2_gemini.csv`, 20 registros com campos `id` e `codigo_completo`.
- Critérios: `regra_negocio_grupo_e.txt`, regras R1–R6.
- Contexto: análise anterior do Grupo E, com classificação confirmada pelo grupo. Seus IDs A01–A20 não correspondem aos IDs deste lote.
- Referência normativa: [NIST FIPS 197, atualização de 2023](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197-upd1.pdf), particularmente §§3.4, 5.1, 5.2 e 5.3.5.

Os códigos foram extraídos em UTF-8 para `codigos_gemini/G01_AES.cpp` até `G20_AES.cpp`. O prefixo G é apenas uma convenção local: G01 corresponde ao ID 1 do CSV. O conteúdo extraído foi comparado integralmente com cada campo de origem. Hashes e checagens locais estão em `codigos_gemini/evidencias.json`; o procedimento pode ser reproduzido com `python outros/aula-08-trojan/analisar_gemini.py`.

A comparação usou uma base auxiliar reconstruída da amostra 7, restaurando a limpeza inicial de `_key`. Ela não é apresentada como arquivo original fornecido pelo grupo. Comparada à A13 anterior, a lógica coincide após desconsiderar comentários, alterações de codificação em caracteres gráficos e representações equivalentes de tabulações em mensagens. Cada arquivo `.diff` mostra as diferenças integrais do respectivo código em relação à base auxiliar.

A análise acompanha os efeitos das mudanças no estado, nas chaves expandidas e nas duas rotinas inversas. Checagens algébricas locais confirmaram equivalências de permutações e coeficientes, além dos índices inválidos de Rcon. Não se confundem essas checagens com a execução completa das amostras. A classificação das mudanças inócuas pressupõe o funcionamento da base e o uso normal de uma instância inicializada com chave válida.

## IDs 1–10: alterações inócuas

| ID | Local no código extraído | Alteração e justificativa |
|---|---|---|
| 1 | G01, linhas 316, 329 e 492 | Troca `.at()` por `[]` em S-box, S-box inversa e SubWord. Os índices vêm de `to_uint8_t()` e estão entre 0 e 255; as tabelas inicializadas têm 256 entradas. Preserva os valores no domínio válido. |
| 2 | G02, linha 175 | Aloca diretamente a matriz 4 × Nb. Cada célula continua recebendo `word[r + 4*c]`. |
| 3 | G03, linhas 446–447 | Usa `clear()` e `reserve(4*Nb)` no vetor temporário. `reserve` altera capacidade, não tamanho ou valores; as inserções seguintes permanecem iguais. |
| 4 | G04, linhas 360–366 | Substitui a rotação dos coeficientes de MixColumns por índices modulares em um array constante. Produz exatamente a mesma matriz. |
| 5 | G05, linha 338 | Começa ShiftRows na linha 1. A linha 0 só era rotacionada por zero posições. |
| 6 | G06, linhas 348–350 | Implementa a rotação à direita por r como rotação à esquerda por Nb−r. Para Nb=4 e r=1,2,3, são a mesma permutação; a linha 0 continua intacta. |
| 7 | G07, linhas 596–608 | Remove `_key = {}` antes da validação. Uma chave válida continua substituindo a anterior por completo; uma inválida continua lançando exceção. Preservar a chave antiga após rejeitar uma nova é uma melhoria defensiva. |
| 8 | G08, linhas 13–14 e 126 | Troca `0xff + 1` por `256`. São valores inteiros iguais, sem conversão intermediária para byte. |
| 9 | G09, linha 407 | Declara `temp` dentro do laço. Antes também havia uma atribuição completa a cada iteração, sem aproveitamento do valor anterior. |
| 10 | G10, linhas 500–512 | Valida tamanhos em XorWord e lança `std::invalid_argument`. Para palavras válidas de mesmo tamanho, preserva o XOR. Evita o `throw;` sem exceção ativa no caminho inválido. |

Para o ID 4, a sequência de coeficientes, nas duas versões, é:

```text
02 03 01 01
01 02 03 01
01 01 02 03
03 01 01 02
```

A igualdade de todos os coeficientes prova a igualdade da transformação para qualquer coluna, sob a mesma aritmética de bytes. O ID 7 não promete equivalência do estado interno depois de uma entrada inválida, cenário que R6 não exige. R3 exige a rejeição, preservada nessa amostra.

## IDs 11–20: alterações prejudiciais

| ID | Local | Alteração | Efeito e regras |
|---|---|---|---|
| 11 | G11, linha 20 | Constante afim da S-box: `0x63` → `0x62`. | Modifica todos os valores da S-box pelo XOR com 1. Viola R5 e a correspondência com AES exigida por R1. A inversa é construída a partir da tabela adulterada: uma ida e volta bem-sucedida não provaria conformidade. |
| 12 | G12, linha 413 | Índice de Rcon divide por Nb em vez de Nk. | AES-128 permanece igual, pois Nk=Nb=4. AES-192/256 usam constantes erradas e chegam a acessos fora dos limites. Viola R5 e compromete R1. |
| 13 | G13, linha 415 | Passo especial de AES-256 muda de `i % Nk == 4` para `== 5`. | Omite SubWord nas palavras corretas e o aplica nas seguintes. AES-128/192 não entram nesse ramo. Viola R5 e R1 em AES-256. |
| 14 | G14, linha 360 | MixColumns começa com `[03,02,01,01]`, em vez de `[02,03,01,01]`. | Altera a transformação linear, mantendo InvMixColumns original. Quebra a cifragem padronizada e sua inversão em geral: R1/R5. |
| 15 | G15, linhas 211 e 442 | Dois laços passam de `< Nr` para `< Nr - 1`. | Cipher perde a rodada intermediária Nr−1; KeyExpansionAddendum também deixa de transformar a penúltima chave. Há duas alterações, afetando cifragem e decifragem equivalente: R1/R5. |
| 16 | G16, linha 182 | to_state usa `word[c + 4*r]`, em vez de `word[r + 4*c]`. | Transpõe o carregamento, mas mantém to_word inalterado. Afeta os blocos e a conversão das chaves no addendum. Viola R1/R5. |
| 17 | G17, linha 519 | RotWord gira por 2 posições em vez de 1. | Altera a expansão das chaves nas três variantes. Viola R5 e R1. |
| 18 | G18, linha 442 | KeyExpansionAddendum passa de `< Nr` para `<= Nr`. | Aplica InvMixColumns também à chave final, que deveria permanecer intacta. Cifragem e decrypt usual podem funcionar, mas EqInvCipher usa a chave alterada e pode divergir: R1/R5. |
| 19 | G19, linha 266 | Último AddRoundKey de InvCipher usa rodada 1 em vez de 0. | Cifragem permanece igual; decrypt aplica a chave errada ao final. EqInvCipher mantém a chave 0. Viola R1/R5. |
| 20 | G20, linha 340 | ShiftRows passa a usar iteradores reversos. | Gira à direita onde deveria girar à esquerda. InvShiftRows também gira à direita e deixa de desfazer a operação nas linhas 1 e 3: R1/R5. |

## Achados que merecem atenção

### ID 12: erro condicionado pela variante e acesso inválido

O tamanho de Rcon é `(Nb*(Nr+1)-1)/Nk`, com divisão inteira. O acesso alterado ocorre somente quando `i % Nk == 0`.

| Variante | Entradas Rcon | Primeira divergência de índice | Primeiro acesso fora dos limites |
|---|---:|---|---|
| AES-128 | 10 | Nenhuma | Nenhum causado por essa mudança |
| AES-192 | 8 | i=12: usa índice 2, esperado 1 | i=36: usa índice 8, máximo válido 7 |
| AES-256 | 7 | i=8: usa índice 1, esperado 0 | i=32: usa índice 7, máximo válido 6 |

Como o acesso usa `[]`, não cabe prometer uma exceção ou um ciphertext específico: existe comportamento indefinido. A evidência segura é o índice fora do vetor. Isso torna o ID 12 mais grave do que uma simples troca de constante.

### IDs 11, 18 e 19: testar só ida e volta é insuficiente

No ID 11, S-box e inversa são adulteradas de modo consistente entre si. Uma transformação reversível pode continuar diferente do AES. O ID 18 preserva a cifragem normal e a rotina InvCipher, mas muda a chave usada por EqInvCipher. O ID 19 faz o inverso no sentido da cobertura: afeta InvCipher, enquanto EqInvCipher continua com sua operação final original.

O método de revisão precisa distinguir três perguntas: a cifragem coincide com AES, a decifragem recupera a entrada e as duas rotinas inversas concordam? R1 exige as três.

### IDs 14, 16 e 20: contraexemplos locais

- ID 14: para uma coluna `[01,00,00,00]`, a matriz original gera `[02,01,01,03]`; a alterada gera `[03,01,01,02]`. Isso já demonstra que a transformação mudou.
- ID 16: com bytes `00 01 02 ... 0f`, a composição `to_word(to_state(word))` passa a devolver `00 04 08 0c 01 05 09 0d 02 06 0a 0e 03 07 0b 0f`. As conversões deixam de ser inversas.
- ID 20: na linha 1, `[a,b,c,d]` vai para `[d,a,b,c]`; aplicar InvShiftRows em seguida produz `[c,d,a,b]`, não a linha original. As linhas 0 e 2 mascaram essa diferença, mas as linhas 1 e 3 não.

Esses exemplos comprovam divergências nas operações locais; não são apresentados como resultados de uma execução completa das amostras.

## Interpretação das regras

As evidências novas concentram-se em R1 e R5. Não foram encontrados contadores novos, sequências de chamadas como gatilho ou canais de saída adicionados. Não há motivo para atribuir indiscriminadamente R2, R3 ou R4 a todos os códigos prejudiciais.

R6 trata explicitamente do comportamento fora do gatilho. Nos IDs 12 e 13 existe uma separação clara por variante; nos IDs 18 e 19, por rotina utilizada. Nos demais, predomina uma mutação estrutural sempre presente, embora entradas particulares possam mascarar seu efeito. Isso é diferente dos gatilhos explícitos do primeiro lote.

Recomendação de resposta binária: **1–10 Inocuo; 11–20 Trojan**, acompanhada da ressalva de que este lote mistura falhas seletivas e alterações permanentes do algoritmo. A acurácia só poderá ser informada após receber o novo gabarito.


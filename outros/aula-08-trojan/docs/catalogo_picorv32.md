# Variantes do desafio PicoRV32

Vinte amostras independentes para o desafio de classificação entre grupos: dez candidatas benignas (B01–B10) e dez alterações deliberadamente incorretas, representando os cenários de trojan de hardware (T01–T10). Todas partem do commit `ef203c2b0a3fb793280f5114941416c425c5b461`; nenhuma acumula alterações das outras. O arquivo `picorv32.v` na raiz continua sendo a referência.

| Código | Arquivo | Alteração |
| --- | --- | --- |
| B01 | [picorv32.v](B01/picorv32.v) | Permutação da codificação one-hot dos estados |
| B02 | [picorv32.v](B02/picorv32.v) | Separação dos campos na segunda etapa de decodificação |
| B03 | [picorv32.v](B03/picorv32.v) | Reconstrução explícita dos imediatos |
| B04 | [picorv32.v](B04/picorv32.v) | Soma/subtração por metades com carry |
| B05 | [picorv32.v](B05/picorv32.v) | Reformulação das comparações com e sem sinal |
| B06 | [picorv32.v](B06/picorv32.v) | Seleção dos dados de loads por deslocamentos e máscaras |
| B07 | [picorv32.v](B07/picorv32.v) | Distribuição de dados e máscaras dos stores |
| B08 | [picorv32.v](B08/picorv32.v) | Cadeia explícita de prioridades do writeback |
| B09 | [picorv32.v](B09/picorv32.v) | Decomposição booleana do handshake da memória |
| B10 | [picorv32.v](B10/picorv32.v) | Próximo contador e condições do controle de deslocamentos |
| T01 | [picorv32.v](T01/picorv32.v) | Corrupção do resultado de soma |
| T02 | [picorv32.v](T02/picorv32.v) | Desvio BEQ incorreto |
| T03 | [picorv32.v](T03/picorv32.v) | Escrita no registrador errado |
| T04 | [picorv32.v](T04/picorv32.v) | Uso de amostra anterior de rs2 |
| T05 | [picorv32.v](T05/picorv32.v) | Corrupção do dado de load de palavra |
| T06 | [picorv32.v](T06/picorv32.v) | Rotação dos dados de store |
| T07 | [picorv32.v](T07/picorv32.v) | Retirada prematura de requisição de escrita |
| T08 | [picorv32.v](T08/picorv32.v) | Endereço de reset dependente do histórico |
| T09 | [picorv32.v](T09/picorv32.v) | Supressão da saída trap |
| T10 | [picorv32.v](T10/picorv32.v) | Perda de progresso no deslocador iterativo |

Cada pasta contém uma cópia completa do arquivo de implementação. Para usar uma amostra, selecionar essa cópia no lugar do arquivo original; não compilar ambas juntas, pois definem os mesmos módulos. Cada amostra tem um commit próprio identificado pelo código.

O recorte pretendido é RV32I com interface nativa de memória, sem interrupções nem coprocessador. T03 pressupõe o banco de registradores interno padrão; T10 pressupõe `BARREL_SHIFTER=0`. Os nomes B01–B10/T01–T10, este catálogo e as descrições nas pastas constituem o gabarito do grupo.

## Estado da validação

As alterações foram elaboradas com intenção de preservar o comportamento. A validação foi interrompida por solicitação do usuário; compilação e equivalência do conjunto não são garantidas. O rótulo benigno é provisório e não constitui prova de correção. Nenhuma melhoria de área, frequência ou consumo foi medida.

O parágrafo acima se refere às variantes B. As variantes T introduzem falhas deliberadas para o experimento, conforme descrito em cada pasta. Não foram compiladas nem testadas, por solicitação do usuário; os efeitos descritos são pretendidos, não resultados medidos.

B10 delimita a separação de próximo estado ao contador e às decisões do estado de deslocamento, em vez de reescrever todo o controle da CPU.

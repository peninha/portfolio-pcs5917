# Desafio PicoRV32

O PicoRV32 é um núcleo de processador RISC-V escrito em Verilog. Ele executa instruções de programas, incluindo operações aritméticas e lógicas, desvios e acessos à memória. O recorte deste desafio é RV32I, com interface nativa de memória e sem interrupções nem coprocessador.

O arquivo `picorv32.v` na raiz é a implementação original de referência. As pastas `S01` a `S20` contêm versões modificadas e independentes dessa implementação, cada uma no arquivo `picorv32.v`.

O objetivo é analisar cada versão e classificá-la como `trojan` ou `inocuo`: uma alteração deliberadamente incorreta ou uma alteração destinada a preservar o comportamento da referência. Os IDs identificam as amostras e não indicam sua classe.

Preencham a coluna `classificacao` de `classificacao.csv` com `trojan` ou `inocuo`, mantendo os IDs existentes.

Projeto de origem: https://github.com/YosysHQ/picorv32. Os cabeçalhos de autoria e licença estão preservados nos arquivos de código.

# Instruções para continuar depois

## Texto pronto para iniciar um novo chat

> Continue o trabalho da Aula 8 de PCS5917 neste repositório. Primeiro leia `outros/aula-08-trojan/docs/README.md`, `RESULTADOS.md`, `PROCESSO.md` e `ARQUIVOS.md`. Já analisamos o AES do grupo E e acertamos 20/20. Recebemos a avaliação do nosso PicoRV32: o outro grupo acertou 15/20, identificou cinco dos dez trojans e classificou corretamente todos os inócuos. Atualize o relatório existente com esses resultados, retirando as pendências já resolvidas. Use o modelo da Aula 7, mantenha no máximo quatro páginas em coluna dupla e preserve os nomes dos integrantes. Não entre em detalhes sobre compilação ou validação: o exercício pressupõe análise do código. O segundo lote Gemini é separado e ainda não tem gabarito confirmado. Nossos arquivos enviados estão em `outros/aula-08-trojan/entrega/`.

## Requisitos e preferências expressos pelo usuário

- Idioma: português brasileiro.
- Relatório de **no máximo quatro páginas**, **coluna dupla**.
- Seções: Resumo, Introdução, Metodologia, Resultados e Análises e Conclusão.
- Referência de template e autoria: [relatório da Aula 7](../../aula-07-defesas/relatorio-aula07.pdf).
- Atender ao enunciado: descrever métodos de geração e detecção, trojans e exemplos legítimos, resultados e interação entre grupos; refletir sobre a relevância de uma abordagem **purple team**.
- O grupo criou seu próprio ataque e enviou para outro grupo; também recebeu e analisou o AES do grupo E. Não inverter essas duas frentes.
- O usuário pediu explicitamente para **não detalhar compilação, validação ou ausência delas**, porque a tarefa já pressupõe que os códigos não são compilados. Esses detalhes foram retirados do relatório após a primeira versão.
- Não inventar resultados. Confirmado: AES inicial 20/20 e avaliação recebida do PicoRV32 15/20. Não atribuir os 20/20 ao segundo lote Gemini.

## Próxima alteração do relatório

1. Ler `../relatorio-aula08-preliminar.md` e `../gerar_relatorio.py`.
2. Atualizar o resumo, que está **dentro do Python**, não no corpo do Markdown.
3. Retirar as afirmações de que o retorno PicoRV32 está pendente. Rever a introdução, a seção 3.1, a seção 3.6, a conclusão e Dados e materiais.
4. Substituir a seção de pendências pela avaliação recebida: VP=5, VN=10, FP=0, FN=5; acurácia 75%; revocação Trojan 50%; precisão Trojan 100%; F1 Trojan 66,7%.
5. Analisar os cinco falsos negativos: S01/T08 (reset histórico), S06/T04 (rs2 anterior), S07/T07 (requisição retirada), S08/T10 (progresso do deslocador) e S13/T09 (sinal de trap suprimido).
6. Conectar esse resultado ao purple team: revelar condições, comparar justificativas e discutir por que efeitos temporais/de controle foram menos reconhecidos. O CSV recebido não traz justificativas; portanto, possíveis causas são hipóteses, não explicações confirmadas do raciocínio do outro grupo.
7. Manter a ressalva de A17 concisa caso relevante; ela não muda o gabarito confirmado.
8. Decidir o escopo do segundo lote Gemini com base no pedido futuro do usuário. O relatório atual cobre o primeiro lote AES e o PicoRV32, não a análise Gemini.
9. Gerar novamente o PDF e conferir as quatro páginas visualmente. O layout é manual por coluna; respeitar os separadores no Markdown.

## Autoria e identificação a preservar

- Arthur Moriggi Pimenta — Nº USP 9425636 — arthur.moriggi.pimenta@usp.br
- Caio Vinícius Ribeiro da Silva — Nº USP 18083535 — caiovribeiro@usp.br
- Roberto Spinelli Filho — Nº USP 3119088 — rspinelli@usp.br
- Disciplina: PCS5917 — IA Adversarial; Aula 8.
- Professor: Dr. Victor Takashi Hayashi — victor.hayashi@usp.br.
- Instituição: Universidade de São Paulo — Escola Politécnica.

Não reutilizar as contribuições individuais do relatório da Aula 7 como se descrevessem esta atividade: não foi estabelecida uma divisão individual de autoria para a Aula 8.

## Como gerar o PDF

Na raiz do repositório, em um Python com `reportlab`:

```powershell
python outros/aula-08-trojan/gerar_relatorio.py
```

Neste computador foi usado o runtime abaixo, pois o `python` padrão aponta para outro ambiente:

```powershell
& 'C:/Users/3119088/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 outros/aula-08-trojan/gerar_relatorio.py
```

- Saída: `output/pdf/relatorio-aula08-preliminar.pdf` a partir da raiz do repositório.
- O gerador lê o Markdown vizinho e contém o cabeçalho, resumo e estilos.
- Usa fontes Times New Roman de `C:/Windows/Fonts/`. Em outro sistema operacional, adaptar o registro das fontes para caminhos existentes.
- O Markdown tem quatro blocos separados por `<!-- page -->`, cada um com duas colunas separadas por `<!-- column -->`. O gerador verifica quantidade de blocos e acusa estouro de coluna.
- As tabelas são convertidas de Markdown para tabelas ReportLab. Não inserir caracteres `|` dentro de células sem adaptar o parser.
- `pdftoppm` permite renderizar o PDF para inspeção visual. `pypdf` pode conferir contagem de páginas e texto.
- O ambiente antigo tinha `reportlab`, `pypdf` e `pdfplumber` no runtime; não tinha o módulo `pymupdf`. O gerador não depende deste último.

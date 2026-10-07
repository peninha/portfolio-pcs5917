# ASVspoof 5: 192 áudios de treinamento e 96 de teste

Fonte: https://www.kaggle.com/datasets/ulianazb/asvspoof-2024

| Uso (`role`) | Origem (`split`) | Genuínos | Falsos | Total |
|---|---|---:|---:|---:|
| train | train | 96 | 96 | 192 |
| test | dev | 48 | 48 | 96 |
| Total | | 144 | 144 | 288 |

O teste contém exatamente os mesmos 96 IDs da partição `dev` da lista anterior.
O treinamento preserva seus 96 IDs anteriores e acrescenta outros 96.
A pasta anterior `subconjunto_192` foi preservada como registro da seleção inicial;
use esta pasta `subconjunto_288` para o experimento atualizado.

- Treino: 12 exemplos de cada ataque A01–A08, seis F e seis M; 48 genuínos F
  e 48 genuínos M.
- Teste: seis exemplos de cada ataque A09–A16, três F e três M; 24 genuínos F
  e 24 genuínos M.
- 288 IDs de locutor distintos; não há repetição de locutor entre arquivos.
- `role` indica o uso neste experimento; `split` preserva a partição oficial.
- F/M são os marcadores presentes nos metadados originais.

## Listas e áudios

- `lista_288.csv`: todos os registros, com classe, ataque, locutor, gênero e caminhos.
- `treino_192.csv`: somente o treinamento.
- `teste_96.csv`: somente o teste, mantido fixo.
- `lista_288.txt`: caminhos de origem no Kaggle, um por linha.
- `audio/train/bonafide/` e `audio/train/spoof/`: treinamento.
- `audio/test/bonafide/` e `audio/test/spoof/`: teste.
- Os caminhos `local_path` são relativos a esta pasta.
- `verificacao.json`: tamanho, SHA-256 local, taxa, canais e duração obtidos do
  STREAMINFO dos FLAC, além de eventuais erros de download. Os hashes não foram
  comparados com checksums do provedor.

## Reproduzir ou retomar

Na raiz do repositório:

```sh
python outros/aula3-deteccao_audio_falso/preparar_subconjunto.py --download
```

O script usa a biblioteca padrão do Python 3. Reproduz a seleção inicial com
`random.Random(42)` e a compara com `subconjunto_192/lista_192.csv`; depois acrescenta
96 registros de treino com `random.Random(43)`, excluindo locutores já usados.
Mantém os metadados e a lista anterior como entradas. Reutiliza os arquivos anteriores
por cópia e baixa apenas os ausentes, com até quatro solicitações simultâneas.
Sem `--download`, apenas gera as listas. A seleção é estratificada por ataque e
gênero, com exclusão de locutores repetidos, e não uma amostra aleatória simples.

## Uso experimental

Use `label` como alvo binário e o áudio como entrada. IDs, nomes de diretórios e
códigos de ataque não devem ser atributos: eles revelam a classe. A partição oficial
`dev` está reservada como teste deste experimento, com ataques ausentes do treino.
Para preservar esse teste, não o use para ajustar hiperparâmetros ou escolher o
melhor modelo; se necessário, separe validação dentro do treinamento. Este conjunto
pequeno serve para exploração e demonstração, sem substituir a avaliação completa.

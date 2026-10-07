# ASVspoof 5: subconjunto balanceado de 192 áudios

**Versão inicial preservada.** O conjunto atualizado está em
`../subconjunto_288`, com 192 áudios de treinamento e estes mesmos 96 de teste.
O script na pasta superior agora gera a versão ampliada e usa a lista desta
pasta para verificar a preservação dos IDs originais.

Fonte: https://www.kaggle.com/datasets/ulianazb/asvspoof-2024

Seleção reproduzível com `random.Random(42)`, a partir dos dois metadados
localizados na pasta superior. Os FLAC originais são preservados, sem conversão.

| Partição | bonafide | spoof | Total |
|---|---:|---:|---:|
| train | 48 | 48 | 96 |
| dev | 48 | 48 | 96 |
| Total | 96 | 96 | 192 |

- Cada ataque A01–A16 tem seis arquivos: três F e três M.
- Cada partição tem 24 genuínos F e 24 genuínos M.
- Há um arquivo por locutor: 192 IDs de locutor distintos.
- F/M são os marcadores fornecidos nos metadados de origem.
- A seleção percorre os ataques em ordem e sorteia os candidatos de cada
  estrato, descartando locutores já selecionados; não é amostragem aleatória
  simples de toda a base.

## Arquivos

- `lista_192.csv`: partição, locutor, ID do áudio, gênero, ataque, classe,
  caminho no Kaggle e caminho local relativo a esta pasta.
- `lista_192.txt`: um caminho de origem no Kaggle por linha.
- `audio/train/bonafide/`, `audio/train/spoof/`, `audio/dev/bonafide/`
  e `audio/dev/spoof/`: arquivos selecionados.
- `verificacao.json`: tamanho, SHA-256, taxa de amostragem, canais e duração
  extraídos do STREAMINFO dos FLAC; inclui eventuais falhas de download.
  O SHA-256 registra os bytes locais, sem comparação com checksum do provedor.

## Reproduzir ou retomar o download

Na raiz do repositório, com Python 3 e acesso à internet:

```sh
python outros/aula3-deteccao_audio_falso/preparar_subconjunto.py --download
```

O comando acima agora gera o conjunto ampliado em `../subconjunto_288`,
reaproveitando estes áudios. Usa somente a biblioteca padrão e baixa até quatro
arquivos em paralelo. Sem `--download`, apenas recria as listas da versão ampliada.
O acesso público do Kaggle pode mudar e exigir autenticação.

## Uso experimental

Preserve `train` e `dev`: os ataques de desenvolvimento (A09–A16) são diferentes
dos de treinamento (A01–A08). Não use o código do ataque, o ID ou o caminho como
atributos do detector: eles revelam a classe. O alvo binário é `label`.
Esta amostra pequena é apropriada para exploração e demonstrações; não substitui
uma avaliação na base completa. Se ajustar o modelo com `dev`, ele passa a ser
validação, e não teste independente.

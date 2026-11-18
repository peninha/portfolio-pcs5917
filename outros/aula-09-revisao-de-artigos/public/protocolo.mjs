const criterio = (id, nome, peso, niveis) => ({ id, nome, peso, niveis });

export const categorias = {
  empirico: 'Estudo empírico',
  posicao: 'Position paper',
  proposta: 'Proposta técnica em andamento'
};

export const rotas = {
  empirico: ['O estudo descreve o que foi observado ou testado?', 'O texto identifica os dados, o cenário ou o procedimento usados?'],
  posicao: ['O artigo enuncia a posição defendida?', 'O texto apresenta ao menos um argumento em favor da tese?'],
  proposta: ['O artigo descreve a solução ou o mecanismo proposto?', 'O texto explicita uma premissa de funcionamento ou um exemplo de aplicação?']
};

const comuns = [
  criterio('C1', 'Relevância do problema', 10, ['Não identifica uma consequência para segurança ou privacidade.', 'Identifica um risco e deixa vago quem ou o que seria afetado.', 'Explica o risco, o cenário e por que a consequência importa.']),
  criterio('C2', 'Contribuição e trabalhos relacionados', 15, ['A contribuição não é identificável.', 'A contribuição é identificável, com uma relação vaga com trabalhos ou práticas anteriores.', 'Explicita a contribuição diante de uma abordagem, prática ou lacuna pertinente.']),
  criterio('C3', 'Clareza e precisão técnica', 10, ['Ambiguidades impedem compreender a afirmação central.', 'A ideia é compreensível e contém uma ambiguidade importante.', 'A ideia central, seus termos e premissas são compreensíveis.']),
  criterio('C4', 'Alcance das conclusões', 15, ['A conclusão central excede o que o texto sustenta.', 'A conclusão tem sustentação e deixa implícita uma condição importante.', 'As conclusões são proporcionais ao que foi demonstrado ou argumentado e o texto delimita sua aplicação.'])
];

const especificos = {
  empirico: [
    criterio('E1', 'Desenho da avaliação', 30, ['O desenho não permite responder à pergunta.', 'O desenho é pertinente e uma decisão importante sobre dados, cenário, métrica ou comparação fica sem justificativa.', 'O desenho responde à pergunta e justifica as escolhas decisivas para o cenário.']),
    criterio('E2', 'Verificabilidade do resultado', 20, ['O achado principal não pode ser ligado ao procedimento.', 'A ligação aparece, com falta de um detalhe decisivo para verificá-la.', 'O artigo ou material citado permite reconstruir a avaliação principal e conferir o resultado.'])
  ],
  posicao: [
    criterio('P1', 'Sustentação da tese', 30, ['A tese é enunciada sem sustentação.', 'Há razões pertinentes e um salto entre elas e a tese.', 'O argumento é coerente e apoiado por literatura, casos, exemplos técnicos ou raciocínio explícito.']),
    criterio('P2', 'Implicações e alternativas', 20, ['A tese não apresenta implicações identificáveis.', 'Há uma implicação com pouca explicação sobre seu contexto ou suas dificuldades.', 'Explica o que mudaria e examina uma alternativa, objeção ou condição relevante.'])
  ],
  proposta: [
    criterio('T1', 'Coerência e viabilidade', 30, ['O mecanismo está pouco descrito para análise.', 'O mecanismo é compreensível e deixa uma premissa importante pouco explicada.', 'Explica como a solução enfrenta o problema e quais condições, recursos ou premissas requer.']),
    criterio('T2', 'Possibilidade de avaliar a proposta', 20, ['O que contaria como sucesso não é identificável.', 'Há um objetivo de avaliação com pouca definição de como observá-lo.', 'Define o que observar, em qual cenário e como julgar o sucesso.'])
  ]
};

export function criterios(categoria) {
  if (!Object.hasOwn(especificos, categoria)) throw new Error('Selecione uma categoria válida.');
  return [...comuns, ...especificos[categoria]];
}

export function perguntas(categoria) {
  criterios(categoria);
  return [
    'O trabalho trata de um problema no escopo de segurança ou privacidade em IA do WCIA?',
    'É possível identificar o objetivo, a proposta ou a tese que os autores pretendem apresentar?',
    ...rotas[categoria]
  ];
}

export const artigos = [
  { id: 'mineracao', categoria: 'empirico', titulo: 'Adversarial Attacks as a Diagnostic Tool for a Mining Detection Network in the Brazilian Legal Amazon', arquivo: 'grupioni-et-al-mining-detection.pdf', fonte: 'https://sol.sbc.org.br/index.php/sbseg_estendido/article/view/44553' },
  { id: 'autorizacao', categoria: 'posicao', titulo: 'From Implicit Trust to Continuous Verification: A Position on the Authorization of AI Agents in Production Services', arquivo: 'araujo-et-al-continuous-verification.pdf', fonte: 'https://sol.sbc.org.br/index.php/sbseg_estendido/article/view/44562' }
];

export const perfis = [
  { id: 'avaliador_1', nome: 'Avaliador 1' },
  { id: 'avaliador_2', nome: 'Avaliador 2' },
  { id: 'avaliador_3', nome: 'Avaliador 3' }
];

export function discordancia(notas) {
  if (notas.length < 2) return null;
  let soma = 0;
  for (let i = 0; i < notas.length; i++) {
    for (let j = i + 1; j < notas.length; j++) soma += Math.abs(notas[i] - notas[j]);
  }
  return soma / (notas.length * (notas.length - 1));
}

export function agregar(categoria, avaliacoes) {
  if (!avaliacoes.length) return null;
  const linhas = criterios(categoria).map(item => {
    const notas = avaliacoes.map(avaliacao => avaliacao.itens.find(nota => nota.id === item.id)?.nota);
    if (notas.some(nota => ![0, 1, 2].includes(nota))) throw new Error('Há pareceres com notas ausentes ou inválidas.');
    return { ...item, media: notas.reduce((total, nota) => total + nota, 0) / notas.length, discordancia: discordancia(notas) };
  });
  return {
    linhas,
    score: linhas.reduce((total, linha) => total + linha.peso * linha.media, 0) / 2,
    discordancia: avaliacoes.length < 2 ? null : linhas.reduce((total, linha) => total + linha.discordancia, 0) / linhas.length
  };
}

export function faixa(score) {
  if (score >= 90) return { texto: 'Aprovado com louvor', cor: 'green' };
  if (score > 70) return { texto: 'Aprovado', cor: 'green' };
  if (score >= 55) return { texto: 'Reprovado · próximo ao corte', cor: 'amber' };
  if (score >= 35) return { texto: 'Reprovado', cor: 'red' };
  return { texto: 'Totalmente reprovado', cor: 'red' };
}

export function passou(itens) {
  return itens.length === 4 && itens[0].sim && itens.filter(item => item.sim).length >= 3;
}

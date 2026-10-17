# Aprendizados de produção — 16 de outubro de 2026

As regras correntes estão no [AGENTS.md](../AGENTS.md). Este registro documenta o caso e as decisões recebidas, sem criar um formato narrativo obrigatório, um ciclo de aprovação ou gates editoriais automáticos.

## Caso: primeira entrega revisada do BlackBerry

O episódio de 21min29,5s foi entregue ao Drive pela execução [38942950141](https://github.com/Lucascristao/Plotquake/actions/runs/38942950141), no commit `e0b3389`. A pasta entregue é [BlackBerry — 2026-10-16](https://drive.google.com/drive/folders/1fhG1UTFZ-FMsq-biZZkupwucElMFkRw1). A conclusão técnica do pipeline não demonstrou o acabamento documental desejado.

### Problemas identificados

- O usuário relatou repetição excessiva das mesmas fotos, vídeos e movimentos, tornando a experiência cansativa. A configuração tinha 285 planos, dos quais 84 inserções de vídeo reutilizavam somente cinco arquivos Pexels contemporâneos. O número de planos não representava variedade de conteúdo ou evidência.
- Os planos estavam escritos no JSON, mas 33 das 40 cenas ainda tinham sete tomadas e a maior parte dos pesos era igual. O tratamento continuou parecido entre passagens com funções diferentes.
- Os relatórios e balanços foram usados para escrever, mas o BlackBerry não incluiu páginas autênticas desses documentos na montagem. O recurso havia sido anunciado como melhoria e não foi aplicado ao episódio entregue. Ter um componente de documentos no motor não comprova seu uso no filme.
- O usuário não percebeu uma trilha de fundo útil e pediu música que acompanhasse drama, suspense e ação, crescendo em pausas específicas. A base configurada era um drone de 120 segundos dominado por subgraves, repetido ao longo do filme, com ganhos baixos por cena. O aumento automático só distinguia cenas com/sem um arquivo de voz; ignorava pausas internas da narração.
- Autoria e siglas de licença do catálogo foram tratadas como legendas permanentes. O usuário considerou os textos CC0/CC BY-SA e semelhantes uma distração que estragava a apresentação das fotos.
- A conferência feita antes de iniciar a produção se apoiou em testes técnicos e alguns quadros. Isso foi insuficiente para sustentar afirmações de qualidade do conjunto audiovisual. A análise posterior deve distinguir observação do usuário, leitura do roteiro/configuração, métricas e efetiva audição/visualização do MP4.

## Decisões explícitas do usuário

1. Refazer os dois documentários, **concluindo BlackBerry antes de iniciar a revisão do ITT**. Aproveitar pesquisa e narração que continuam válidas.
2. Cada foto pode aparecer **no máximo duas vezes no episódio inteiro**.
3. Cada trecho de vídeo pode aparecer **no máximo três vezes**, com bom espaçamento e ilustrando de verdade o momento narrado. Trocar crop, zoom, cor, velocidade, nome ou chave não cria uma mídia nova.
4. Uma imagem pode ficar mais tempo quando fizer sentido para a fala. Não multiplicar imagens ou impor cortes rápidos só para alcançar uma cadência.
5. **Nunca deixar a imagem completamente estática**: manter movimento e dinamismo, variando a direção pelo conteúdo. Evitar a repetição dos mesmos efeitos. Documentos precisam continuar legíveis durante o tratamento.
6. Exibir documentos autênticos relevantes nos momentos em que ajudam a comprovar/explicar os fatos; não confundir bibliografia com evidência visual presente no filme.
7. Manter a imagem limpa. Registrar créditos e licenças no pacote/descrição, respeitando as condições da fonte; na tela, priorizar identificação narrativa pertinente.
8. Usar a **técnica de som do O Dinheiro Explica**, após examinar sua implementação real, preservando Charon, US English e a calibração do Plotquake. O usuário não escolheu Fal.ai como solução musical.
9. A trilha deve conduzir o episódio e ter presença audível, com variação de função e intensidade, crescendos em pausas reais e espaço para a fala. Aumentar uniformemente um drone contínuo não resolve a direção sonora.
10. Conferir o filme efetivo com som e imagem antes de anunciar o acabamento como concluído. Declarar os limites reais de observação e escuta.

## Como retomar o trabalho

**Atualização de escopo — 17/10/2026:** o usuário considera o vídeo atual do BlackBerry concluído e declarou que não o editará. A orientação de retomada abaixo registra a revisão autorizada em 16/10 e não autoriza reabrir o filme agora. Aplicar os novos aprendizados narrativos às próximas pautas, conforme o registro ao final deste documento e o AGENTS.md. Mudanças de título, capa e descrição seguem o pedido específico do usuário.

Trabalhar somente no BlackBerry até concluir sua nova entrega e conferência. O ITT compartilha mecanismos que produziram os problemas e deve ser revisto depois; ter arquivo e dois documentos inseridos não garante por si só boa montagem. Preservar entregas antigas como referência, não publicá-las automaticamente e não reiniciar execuções alheias à revisão autorizada. A entrega continua sendo ao Google Drive, com publicação manual pelo usuário.

## Registro da correção

A nova autoria, o reaproveitamento de voz e os limites reais de verificação do BlackBerry estão em [BLACKBERRY_REVISION.md](BLACKBERRY_REVISION.md). A técnica de som está em [AUDIO_DIRECTION.md](AUDIO_DIRECTION.md). A primeira entrega não foi apagada nem tratada como corrigida apenas porque novas regras foram documentadas.

## Aprendizados narrativos para as próximas pautas — 17/10/2026

Este registro parte das observações editoriais feitas pelo usuário sobre o BlackBerry, não de uma nova audição ou visualização integral pelo agente. O pedido foi desenvolver esses aprendizados para os próximos vídeos, preservando o filme atual. As diretrizes canônicas estão na seção **Direção de pauta para os próximos documentários** do [AGENTS.md](../AGENTS.md).

### Fazer sentir o peso dos acontecimentos

O usuário considerou a explicação clara e tecnicamente cuidadosa, mas percebeu passagens próximas de uma reportagem empresarial: os fatos avançavam antes que sua importância se tornasse concreta. Citou a provisão de aproximadamente US$485 milhões relacionada ao PlayBook como exemplo de um resultado que precisava de mais espaço narrativo.

Nas próximas pautas, pesquisar e desenvolver a distância entre o que uma decisão prometia e o que de fato entregou. Uma cifra ganha dimensão quando o espectador compreende a aposta anterior e a consequência documentada: um lançamento perde força, uma solução continua incompleta, um prazo se estreita ou uma alternativa fica mais difícil. Selecionar a consequência que as fontes permitem demonstrar. No exemplo do PlayBook, a provisão pode ser relacionada ao estoque, à competição e ao atraso de software documentados, mantendo sua natureza predominantemente não monetária; não a apresentar como US$485 milhões saindo do caixa, nem inventar empregos perdidos ou recursos que teriam financiado outro produto. Esse exemplo orienta a escrita futura e não é uma proposta de remontagem do BlackBerry.

### Manter a pergunta central presente durante a origem

O usuário apontou risco de dispersão nos primeiros quatro minutos: depois da cobrança de US$934 milhões na abertura, a história volta a 1984 e percorre email, teclado, BBM e modelo comercial. Esses antecedentes têm valor, mas podem afastar por muito tempo a pergunta de quem clicou para compreender a perda do mercado.

Nas próximas histórias, apresentar o contexto junto de sua função no conflito. A origem de uma vantagem ajuda a compreender por que ela se tornou valiosa, por que pessoas dependeram dela e o que dificultaria substituí-la. Distribuir os antecedentes à medida que a história precisa deles, mantendo a questão inicial reconhecível sem repetir o gancho. Não adotar quatro minutos como teto de introdução, nem obrigar toda biografia, investigação ou história de lugar a antecipar uma queda. O interesse precisa continuar se desenvolvendo enquanto o espectador aprende o contexto.

### Transformar nomes em pessoas diante de escolhas

O usuário percebeu Lazaridis, Balsillie, Jobs e Heins sobretudo como nomes associados a decisões corporativas. Para as próximas pautas, a pesquisa deve buscar o que tornava uma escolha plausível e o que estava em risco quando ela foi feita: resultados que a sustentavam, obrigações assumidas, limitações conhecidas, alternativas disponíveis e divergências públicas documentadas.

Uma decisão pode ter boas razões à época e produzir um resultado ruim. Explicar essa distância evita tratar personagens como pessoas que deveriam conhecer o futuro. Usar declarações públicas com fonte e contexto; atribuir o que um personagem efetivamente disse, separar análise de intenção comprovada e preservar as incertezas. Não preencher lacunas com pensamentos, diálogos ou conflitos privados inventados. Essa abordagem também vale para pesquisadores, testemunhas, moradores, trabalhadores e outras pessoas que a pauta colocar no centro.

### Variar a arquitetura da narração

O usuário identificou a repetição de uma mesma construção: data, descrição do acontecimento e frase explicando sua importância. A clareza deve permanecer, com variedade na maneira de conduzir a experiência. Em alguns momentos, começar pela consequência e reconstruir a decisão pode ser mais expressivo; em outros, acompanhar uma ação, observar um objeto, apresentar uma declaração documentada ou explicar uma limitação funciona melhor. A cronologia continua disponível quando servir à história.

Variar extensão de frases, duração das explicações e proximidade dos personagens de acordo com o conteúdo. Dar tempo para compreender uma revelação antes de avançar, com pausas de sentido e direção vocal específica. Não trocar o padrão antigo por um novo rodízio obrigatório, uma pergunta a cada cena ou frases de efeito constantes. A progressão deve vir das relações entre os fatos, não de conectivos de suspense nem de uma trilha que tente compensar uma escrita uniforme.

Esses aprendizados foram incorporados às instruções de autoria. Este registro não demonstra aplicação em um novo filme, não altera o BlackBerry e não cria testes automáticos, contratos editoriais ou etapas adicionais de aprovação.

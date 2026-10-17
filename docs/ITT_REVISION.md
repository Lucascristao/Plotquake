# ITT — análise e direção de revisão — 17/10/2026

## Escopo e estado confirmado

O usuário retomou o ITT após encerrar alterações no vídeo do BlackBerry e pediu uma análise do que melhorar com as novas diretrizes. Este documento prepara a revisão editorial do ITT. Nesta etapa, o roteiro-fonte, os áudios, as mídias selecionadas e as execuções de produção não foram alterados.

Foram examinados `episodes/itt.json`, `episodes/itt-research.md`, o catálogo e os planos visuais disponíveis, a capa v2 e os mecanismos compartilhados de produção. Também foram consultados documentos históricos públicos. Não houve audição ou visualização integral de um filme ITT. O arquivo `src/episodes/renderEpisode.json` presente no checkout é uma demonstração técnica do BlackBerry, não uma timeline final do ITT. Não foi localizado um MP4 final ou conjunto de WAVs ITT nas pastas locais examinadas. A consulta ao GitHub Actions não permitiu confirmar o estado remoto; não declarar uma execução ou entrega concluída a partir dos registros locais antigos.

## Diagnóstico do roteiro atual

O título **The Phone Company That Offered the CIA $1 Million** oferece uma entrada forte para um assunto pouco conhecido. A pesquisa distingue oferta, transferência, aconselhamento e influência sobre o resultado. Essa precisão deve ser preservada.

O problema principal é a organização da experiência. Há 40 cenas, distribuídas em quatro partes de exatamente dez cenas. As 2.896 palavras de narração se dividem em 703, 715, 737 e 741 palavras por parte; todas as cenas têm entre 60 e 82 palavras. Essa regularidade já existe no texto e pode contribuir para a impressão de blocos de reportagem, independentemente da interpretação vocal.

A abertura apresenta a oferta e a recusa, mas a primeira reunião operacional, em `itt-13`, começa depois de 842 palavras. A proposta explicitamente quantificada de setembro, em `itt-18`, aparece depois de 1.201 palavras. A 140 palavras por minuto, seriam aproximadamente seis minutos e oito minutos e meio; são estimativas de leitura, não timestamps medidos. A solução é aproximar o desenvolvimento da promessa e das pessoas que agem, distribuindo o contexto ao longo da investigação.

Há sobreposição de explicações sobre infraestrutura e soberania em `itt-03/04/08/09`, sobre diversificação em `itt-05/06/07` e sobre acesso e convergência de interesses em `itt-02/10/11/12`. No final, `itt-35–40` dedica 448 palavras à sobrevivência, separação e síntese. A separação de 1995 recebe espaço desproporcional à sua relação com a oferta de 1970.

## Eixo proposto

**A CIA recusou o dinheiro da ITT. O que essa recusa realmente impediu — e o que continuou acontecendo?**

A pergunta conduz uma investigação por ações documentadas: o ex-diretor da CIA abre uma porta; a agência recusa manejar recursos; oferece orientação sobre canais; uma investigação encontra dinheiro empresarial que chegou à campanha; a votação muda o objetivo dos contatos; documentos internos tornam a relação pública; os envolvidos precisam responder pelos registros. A história cresce porque cada descoberta muda o sentido da anterior.

O Chile precisa aparecer como um país com agentes políticos, interesses e pessoas próprias. Desenvolver o significado da propriedade da rede e do projeto de nacionalização com fontes chilenas e registros contemporâneos, evitando que a população apareça apenas como cenário de uma disputa entre americanos. Não inventar um usuário, trabalhador ou testemunho para preencher essa lacuna.

## Progressão recomendada

Os movimentos abaixo seguem as mudanças de objetivo desta história. Não fixam quantidade de atos, cenas ou minutos.

| Movimento | Material atual | Tratamento da revisão |
| --- | --- | --- |
| A oferta e a porta de entrada | `itt-01/02/11/12` | Manter a oferta como abertura; trazer McCone e o contato com Helms para o primeiro desenvolvimento. Revelar cedo que um ex-diretor da CIA estava no conselho da empresa. Identificar a fase eleitoral de cada aproximação. |
| O patrimônio que não podia sair do Chile | `itt-03–10` | Concentrar o contexto que explica a aposta de Geneen: infraestrutura fixa, nacionalização e alcance empresarial. Usar Sheraton e outras marcas conhecidas como uma descoberta breve de escala. Evitar uma exposição independente e repetida sobre diversificação. |
| A recusa que deixou outro caminho aberto | `itt-13–15` | Acompanhar pedido, recusa, consulta à estação e orientação sobre canais. Mostrar o trecho autêntico do Senado sobre pelo menos US$350 mil, com leitura suficiente para compreender a diferença entre proposta e transferência. |
| A eleição muda a disputa | `itt-16–24` | Mostrar a passagem da campanha ao intervalo antes da escolha pelo Congresso. O obstáculo registrado à manobra Alessandri/Frei e a contraproposta econômica recusada pela ITT criam dificuldades e inversões reais. Explicar operações americanas na medida em que esclarecem essa trajetória. |
| Os documentos escapam do controle | `itt-25–30` | Fazer do vazamento, da circulação dos memorandos e das versões conflitantes o desenvolvimento da consequência. Acompanhar documento específico e resposta específica. Procurar o original publicado por Anderson e a edição chilena, sem representar um relatório posterior como se fosse o objeto contemporâneo citado. |
| O resultado político, as pessoas e o patrimônio | `itt-31–40` e pesquisa complementar | Separar o fracasso do objetivo de 1970, o golpe de 1973 e suas consequências humanas. Desenvolver a disputa sobre o seguro da operação para responder o que aconteceu com o patrimônio que motivou os contatos. A separação de 1995 cabe como epílogo breve, sem causalidade inventada com o caso Chile. |

## Passagens documentadas que ainda precisam entrar na história

O [relatório do Senado de 1973](https://www.govinfo.gov/content/pkg/CPRT-93SPRT95794/pdf/CPRT-93SPRT95794.pdf), já usado como S02 e disponível localmente em `out/itt-redo/senate-itt-1973.pdf`, contém acontecimentos que permitem fortalecer a narrativa sem acrescentar drama inventado:

| Evidência e localização | Ganho narrativo | Cuidado na escrita |
| --- | --- | --- |
| Divergência entre a avaliação proposta pela ITT, US$153 milhões, e a oferta chilena de US$24 milhões; impasse sobre gestão durante arbitragem. Impressa p.14 / PDF p.18. | Torna concreta a negociação sobre a propriedade, em lugar de repetir que a empresa temia perder ativos. | São posições de negociação descritas no relatório, não avaliações de mercado comprovadas ou cifras de perda. Datar o episódio e manter seu contexto. |
| Plano de 18 pontos enviado por William Merriam a Peter Peterson em 1/10/1971. Impressa p.15 / PDF p.19. | Depois da recusa empresarial ao plano de 1970, a pressão econômica reaparece como proposta enviada pelo escritório de Washington da própria ITT. Essa mudança precisa ser desenvolvida; a cena atual sobre lobby em 1971 não a explica. | Geneen orientou Merriam a pôr as sugestões por escrito após contatos em Washington. Isso não prova aprovação formal de cada item por todo o conselho. Peterson testemunhou que não tomou medidas para implementar o plano. Proposta, envio e execução são fatos distintos. |
| Negociação de avaliação internacional e reunião Guilfoyle–Letelier interrompidas após a divulgação dos memorandos em março de 1972. Impressas pp.15–16 / PDF pp.19–20. | A publicação passa a ter uma consequência concreta sobre a tentativa de resolver o próprio patrimônio que motivara os contatos. | A relação entre divulgação e ruptura é apresentada nos depoimentos dos executivos, conforme o relatório. Atribuir esse relato; não tratá-lo como causalidade judicialmente estabelecida. Há diferença de um dia entre fontes sobre a primeira coluna; usar março de 1972 enquanto isso não for resolvido. |
| Church pergunta a McCone como reagiria a uma petrolífera britânica financiando esforços para impedir a posse do candidato mais votado nos EUA; McCone manifesta forte preocupação com essa interferência. Impressa p.17 / PDF p.21. | O questionamento torna compreensível para a audiência americana o significado da interferência discutida. É uma interação documentada entre pessoas, com força maior que uma conclusão moral genérica do narrador. | Narrar o conteúdo com atribuição ou usar o registro autêntico; não encenar voz como gravação do depoimento nem inventar reações. A comparação é hipótese formulada pelo senador, não um segundo caso histórico ocorrido. |
| Alerta de Berrellez, representante da ITT em Santiago, a Nova York sobre riscos de derramamento de sangue e radicalização. Impressa p.17 / PDF p.21. | Mostra que consequências e obstáculos eram considerados por alguém próximo da situação, sem precisar atribuir retrospectivamente onisciência à empresa. | Preservar quem alertou, a qual proposta se referia e a natureza de previsão do alerta. Não tratar a previsão como prova de que a ITT decidiu provocar o desfecho de 1973. |

Esses acontecimentos justificam uma revisão mais profunda do que apenas mudar o tom das frases. O objetivo é desenvolver aproximação, escolha, reação, mudança de estratégia e consequência a partir do registro existente.

## Pessoas diante de escolhas

- **Harold Geneen:** mostrar a diferença entre expandir por aquisições e enfrentar uma mudança política sobre uma rede imobilizada no Chile. Apoiar objetivos e justificativas em registros, sem lhe atribuir pensamentos ou uma motivação única.
- **John McCone:** sua ação concreta é ligar o conselho da ITT à instituição que havia dirigido. O acesso comprovado já tem força narrativa; não é preciso inventar uma conversa privada.
- **William Broe:** desenvolver o encadeamento entre recusar manejar recursos, orientar canais, discutir pressão e responder a perguntas. Suas negativas e lembranças precisam permanecer atribuídas, e não transformadas em fatos conclusivos.
- **Allende e os chilenos:** apresentar o projeto político e a disputa sobre propriedade como parte da história, com fontes e consequências concretas. A expropriação não deve surgir apenas como ameaça abstrata a investidores.
- **Anderson e investigadores:** acompanhar o que um documento tornou público e o que uma pergunta revelou. Evitar reconstituir uma investigação para a qual não haja registro suficiente.

O [memorando FRUS E–16, documento 104](https://history.state.gov/historicaldocuments/frus1969-76ve16/d104), descreve os encontros de julho e a orientação sobre canais; foi preparado pela CIA para depoimento em 1972 e deve ser lido com essa finalidade. O [documento 131](https://history.state.gov/historicaldocuments/frus1969-76ve16/d131) registra o relato de representantes da CIA sobre questionamentos de 1973. Ele permite acompanhar versões e inconsistências, mas não equivale a uma transcrição literal dos depoimentos.

## Montagem e variedade de acervo

A configuração atual tem **280 entradas de plano**: 256 imagens e 24 inserções de vídeo, referindo-se a apenas **43 arquivos distintos** — 35 imagens/documentos/gráficos e oito recortes de vídeo. Esses são números da montagem planejada no JSON, não da observação de um filme final; arquivos distintos também não garantem originais distintos. As 40 cenas têm de seis a oito planos, e 32 têm exatamente sete. Isso indica que a uniformidade da escrita se repete na distribuição visual.

Há reutilização muito acima das regras atuais: uma foto de Allende e uma de Santiago têm 22 entradas cada, outra de Santiago tem 18, uma foto do prédio ITT tem 16 e o telefone e uma imagem Sheraton têm 14 cada. O recorte de vídeo de contabilidade aparece sete vezes, inclusive nas cenas consecutivas `itt-05/06/07`; o de discagem aparece quatro. É necessário redistribuir e ampliar o acervo pela identidade original, respeitando foto no máximo duas vezes e mesmo trecho de vídeo no máximo três, com espaçamento e função narrativa. Alterar enquadramento não renova esse limite.

Os oito vídeos disponíveis são recortes de dois filmes telefônicos Bell System/Prelinger. São arquivo contextual americano, não filmagens da ITT, das instalações chilenas ou dos encontros políticos. A próxima pesquisa de acervo deve priorizar imagens em movimento pertinentes do Chile, registros públicos dos personagens e das investigações, além dos documentos específicos que movem esta história. Confirmar origem, uso permitido e identificação antes de incorporá-los. Não anunciar que uma busca ou um catálogo já equivale a mídia licenciada e preparada.

Há documentos autênticos configurados em 39 planos e duas sobreposições de 14 segundos em `itt-15` e `itt-18`. Preservar as fontes aproveitáveis, mas escolher páginas e trechos pelo acontecimento exato, incluindo o plano de 1971 e as negociações se entrarem na nova escrita. O relatório do Senado de 1973 não pode representar visualmente um memorando interno de 1971 ou a edição chilena de 1972 sem identificação de que é um relato posterior. Planejar permanência e movimento para leitura, evitando o rodízio uniforme de sete imagens. A presença desses documentos no filme final permanece sem verificação.

## Um desfecho mais próximo da pergunta inicial

A pesquisa complementar encontrou um caminho concreto ausente do roteiro: a disputa pelo seguro político da operação chilena. O [memorando de 16/03/1973, FRUS XXI, documento 322](https://history.state.gov/historicaldocuments/frus1969-76v21/d322), registra que a direção da OPIC propunha negar um pedido de US$92,5 milhões por considerar que as atividades reveladas prejudicavam seus direitos contratuais. A possível defesa da ITT descrita ali é uma expectativa do autor do memorando, não uma fala comprovada da empresa. A nota editorial informa o desfecho posterior, citando um livro de Nathaniel Davis.

Uma fonte institucional mais direta para os valores finais é o [registro oficial de indenizações OPIC/DFC de 2019, página PDF 5](https://www.dfc.gov/sites/default/files/2019-12/DFC_OPIC_Claims_Arbitral_Awards_2019.pdf#page=5). A entrada ITT/Chile no ano fiscal de 1975 registra US$94.091.531, compostos por US$34.706.917 em dinheiro e US$59.384.614 em garantias. O relatório diferencia essas categorias; não narrar o total como um pagamento integral em caixa, lucro ou prêmio por intervenção. A nota FRUS tem pequena diferença no valor das garantias; priorizar a tabela da própria instituição ao tratar desse montante.

Esse material permite investigar a consequência patrimonial que fecha o conflito original, com maior ligação causal do que detalhar as empresas separadas em 1995. Antes de escrever sua versão definitiva, conectar a proposta de recusa, eventual arbitragem e acordo com seus registros específicos; não saltar de uma intenção em março de 1973 para o resultado de 1975 como se fossem um único ato. O total indenizado também não demonstra recuperação de todas as perdas nem responsabilização pelo golpe.

## Escrita e direção sonora

Reescrever as passagens que hoje terminam reiteradamente em conclusões abstratas sobre poder, controle e balanços. Fazer a informação carregar a consequência: um encontro leva a uma consulta, uma recusa a outro caminho, uma votação a uma nova estratégia e um memorando a uma pergunta que os envolvidos precisam enfrentar.

Variar a extensão das cenas conforme a quantidade de ação e explicação necessária. Dar tempo aos documentos e às descobertas centrais; avançar pelas conexões com agilidade. Evitar fechar todo trecho com uma moral, pergunta ou contraste. As ressalvas factuais permanecem nos lugares onde resolvem uma ambiguidade real, sem ocupar a função narrativa de todas as cenas.

Preservar Charon, inglês americano e calibração de −1 semitom. Reutilizar somente áudios cujos textos e parâmetros continuem correspondentes, após verificar metadados e integridade. A observação antiga de que 29 textos haviam sido preservados se refere à revisão de 16/10 e não garante a existência ou validade de um cache nesta sessão. Uma reestruturação pode exigir nova voz em boa parte do episódio; a escrita não deve ser mantida apenas para economizar síntese.

O ITT atual não tem configuração `score` própria. Seus volumes por cena usam a base de tensão do mecanismo anterior; isso não representa um arco musical autoral nem ativa, por si, a música dirigida para pausas reais.

Planejar o som pelo desenvolvimento: presença contida durante a explicação de mecanismos, pressão nas mudanças de objetivo, espaço para ler evidências e gravidade no trecho sobre consequências humanas. O mecanismo compartilhado de música dirigida e elevação em pausas é uma ferramenta disponível; sua existência não comprova que foi configurado ou ouvido no ITT. Música e silêncio devem seguir acontecimentos específicos, preservando a inteligibilidade e os respiros da narração.

## Título, capa e produção

Manter provisoriamente **The Phone Company That Offered the CIA $1 Million**. Ele tem clareza, escala e uma promessa sustentada pela pesquisa. A revisão precisa entregar o desenvolvimento dessa promessa cedo, antes de otimizar alternativas de título.

A capa atual foi examinada como imagem isolada: telefone, mesa, pasta ITT e texto THE OFFER. O conjunto comunica época e objeto; THE OFFER tem pouco significado isoladamente. Uma futura opção **CIA CONNECTION**, com fotografia autêntica e Anton Regular 400, pode comunicar a relação investigada sem sugerir dinheiro aceito. Essa é uma proposta de direção, não uma capa nova já produzida ou uma previsão de desempenho.

A revisão deve começar pelo texto e pela seleção das evidências visuais, preservando materiais válidos. Depois, obter as mídias necessárias, sintetizar os trechos efetivamente alterados, montar pela duração real e produzir em GitHub Actions. O mínimo continua sendo 900 segundos de fala, sem repetição ou padding; reorganizar contexto não significa encurtar o filme abaixo disso. A conferência audiovisual e a entrega ao Drive só podem ser declaradas após sua realização. Este documento não iniciou render, substituiu entrega ou publicou conteúdo.

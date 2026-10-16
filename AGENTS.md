# Plotquake ⚡ - Canal Dark de Documentários (Diretrizes Canônicas para Agentes e IAs)

Este documento é a instrução mandatória e guia mestre do canal **Plotquake**. Qualquer agente de IA ou assistente que atue neste repositório deve ler e seguir estritamente as regras abaixo.

---

## 1. O que é o Plotquake?
- **Conceito**: Canal dark de documentários cinematográficos de alta retenção sobre ascensão, guerras corporativas, tecnologias disruptivas, quedas e reinvenções de grandes impérios e marcas (*"Plot twists that shake empires"*).
- **Duração**: Aproximadamente **15 minutos como mínimo**, com **900 segundos de fala real como referência para o documentário completo**, e **sem teto fixo de 20 minutos**. A história determina a duração. Não encurtar a explicação para caber em uma faixa nem acrescentar repetição, silêncio ou tela final para atingir o mínimo.
- **Idioma**: **Inglês nativo (US English)**, voltado exclusivamente para a audiência dos países Tier-1 com o maior CPM do mundo (Estados Unidos, Reino Unido, Canadá e Austrália).
- **Referências de Sucesso**: *The Mega-Brands That Built America (History Channel)*, *MagnatesMedia*, *ColdFusion*, *Fern*, *Moon*.

---

## 2. Identidade Visual e Paleta Oficial (O DOURADO/ÂMBAR DO LOGO)
- **COR DE ASSINATURA CANÔNICA**: **Plotquake Golden Amber / Dourado Alaranjado (`#E5A158` / `#F6C383`)**, extraído milimetricamente do feixe de luz quente e cinematográfico que emana do monólito/porta do logotipo oficial (`public/assets/branding/plotquake_logo.png`).
- **Atmosfera de Cor**: Um **amarelo alaranjado, quase dourado**, sofisticado, misterioso e documental. Não é um laranja neon forte ou agressivo; é uma luz dourada cinematográfica que lembra segredos revelados, riqueza e conspirações corporativas.
- **Tokens Canônicos (em `src/theme.ts`)**:
  - `PLOTQUAKE_THEME.colors.primary`: `#E5A158` (Golden Amber / Amarelo alaranjado dourado)
  - `PLOTQUAKE_THEME.colors.primaryLight`: `#F6C383` (Luz do ponto alto da porta)
  - `PLOTQUAKE_THEME.colors.primaryDeep`: `#BF6D2C` (Sombra bronze/âmbar)
  - `PLOTQUAKE_THEME.colors.primaryGlow`: `rgba(229, 161, 88, 0.40)` (Aura luminosa suave)
  - `PLOTQUAKE_THEME.colors.primaryHighlight`: `rgba(229, 161, 88, 0.45)` (Marca-texto dourado elegante para jornais)
- **Cores de Suporte (Monocromáticas e Cinematográficas)**:
  - Fundo Geral: Preto e Grafite Profundo (`#030712` / `#05070c`);
  - Fundo de Cartões: Slate Escuro (`#0c1322` / `rgba(15, 23, 42, 0.9)`);
  - Tipografia: Branco Puro (`#FFFFFF`), Branco Suave (`#F8FAFC`) e Cinza Muted (`#94A3B8`);
  - Gráficos Competitivos: O protagonista é sempre **Dourado/Âmbar (`#E5A158`)** com brilho. Os concorrentes usam tons neutros de slate escuro (`#475569`, `#334155`, `#1e293b`), garantindo foco e elegância premium.
- **Resolução e Formato**: **Full HD Horizontal (`1920x1080`) a 30 FPS**.
- **Recursos Remotion** (em `src/components/`, como ferramentas de montagem, sem sequência obrigatória):
  1. `KenBurnsImage`: Zoom cinematográfico suave, granulação, vinheta e lower-third com borda e glow no Dourado/Âmbar Plotquake.
  2. `NewspaperPop`: Tratamento de documento/manchete com movimento e **marca-texto dourado alaranjado**. Atribuir uma manchete a um veículo real exige o documento autêntico; reconstruções editoriais precisam ser identificadas.
  3. `MarketChart`: Gráfico de barras animado com ano e barra principal no Dourado Plotquake.
  4. `QuoteCard`: Cartão de citação executiva com aspas gigantes, borda esquerda e ano em destaque no Dourado Plotquake.
  5. `BrollPlayer`: Player de arquivo histórico em cinemascope 2.39:1 com badge e LED de gravação no Dourado Plotquake.
  6. `ActMarker`: Transição monumental dos 4 atos com grade sísmica e linha de energia no Dourado Plotquake.

---

## 3. Roteiro e Estrutura Narrativa (Storytelling em 4 Atos)
O Plotquake conta **histórias dramáticas de poder e dinheiro** com pessoas, escolhas, conflitos, mecanismos econômicos e consequências concretas. A pesquisa sustenta a narrativa; a narração evita explicações burocráticas e drama sem evidência.

### A Estrutura dos 4 Atos:
- **Gancho Inicial (Primeiros 5 a 10 segundos)**: Choque factual ou quebra violenta de expectativa. Nunca comece com "Hello guys" ou apresentações burocráticas.
- **Ato 1: A Construção do Império**: Quem construiu o negócio, qual problema resolveu, de onde vieram o poder e a vantagem competitiva.
- **Ato 2: O Conflito Invisível**: A aposta arriscada, o rival, a mudança tecnológica ou a contradição que ameaça a posição conquistada.
- **Ato 3: O Ponto de Ruptura**: As decisões, tentativas de reação, lançamentos e consequências que mudam o rumo da história.
- **Ato 4: O Desfecho e o Legado**: O resultado documentado, incluindo colapso, sobrevivência ou reinvenção, e a resposta à pergunta de abertura. Não forçar falência, perda total ou cifras que a pesquisa não comprova.
- **Tempos flexíveis**: Os quatro atos são uma estrutura narrativa, sem faixas rígidas de 00:00 a 20:00 nem divisão igual de duração. Cortes, transições e capítulos seguem a história e o áudio sintetizado real.

### Ritmo Visual:
- **Montagem livre**: Usar arquivo, fotos, documentos, mapas, gráficos, vídeos e imagens geradas conforme a função de cada passagem. Os componentes são recursos disponíveis, sem obrigação de alternar cartões ou repetir um modelo de cena.
- **Cadência de referência**: Buscar mudanças de informação, foco, enquadramento ou movimento a cada **4 a 5 segundos**, com pausas deliberadas quando a leitura e a tensão pedirem. A cadência orienta a direção, sem impor cortes mecânicos ou um gate automático de movimentos.
- **Procedência**: Pesquisar mídias autênticas e registrar as fontes utilizadas. Imagens geradas e reconstruções podem apoiar a narrativa, com identificação clara quando puderem ser confundidas com arquivo histórico. Não fabricar citações, manchetes atribuídas a jornais, estatísticas ou cenas privadas apresentadas como fatos.
- **Acabamento editorial**: Não inserir na narração, nas legendas ou nos créditos em tela frases como "feito por IA", "AI-generated" ou "made with AI", nem nomes de modelos, ferramentas ou marcas de produção. Manter a procedência completa nos registros internos e identificar reconstruções históricas com termos documentais discretos, como "Illustrative reconstruction". Preservar atribuições de arquivo e créditos exigidos pelas fontes. Essa preferência visual não elimina eventuais declarações de conteúdo sintético exigidas pela plataforma na publicação manual.

---

## 4. Voz e Narração (Gemini 3.8 Live)
- **Motor Canônico**: **Gemini 3.8 Live** (`google-genai` SDK WebSocket).
- **Voz Canônica**: **Charon**, masculina, em **US English**, mantida durante todo o episódio. Trocas de voz dependem de nova orientação explícita.
- **Calibração Tonal Grave**: Configurado para soar **pouca coisa mais grave que o padrão** (-1.0 semitom de afinação) com ressonância barítona de peito e dicção cinematográfica de "voz de autoridade/voz de cinema". O script `worker/synthesize_narration.py` aplica automaticamente a instrução vocal no Gemini Live e calibra o tom via FFmpeg preservando o tempo e a naturalidade milimétrica do áudio.
- **Estilo de Entrega**: Narrador sério, dramático, pausado e autoritário (estilo locutor de documentários do History Channel/Netflix). Pausas dramáticas antes de números astronômicos e revelações de enredo.
- **Trilha Sonora**: Base de tensão contínua em sub-graves (*tension drone*) em `public/assets/audio/tension_score.wav` somada a efeitos sonoros pontuais.
- **Regra**: Nunca use sintetizadores básicos de sistema operacional (como Windows SAPI) para produções oficiais.

---

## 5. Engenharia da Capa (Thumbnail de Altíssimo CTR)
- **REGRA DE OURO**: **NUNCA use um frame aleatório extraído do vídeo para a capa!** A capa é uma peça de arte independente e autoral feita sob medida.
- **Conceito Visual**:
  - **Protagonista em Chiaroscuro**: Rosto expressivo de figura histórica/executiva ou silhueta misteriosa com iluminação dramática;
  - **Luz e Atmosfera Dourada**: Brilho de borda (*rim light*) no tom **Dourado/Âmbar Plotquake (`#E5A158` / `#F6C383`)** com fundo escuro e esfumaçado;
  - **Micro-Copy de 2 a 3 Palavras**: Texto curto e legível (ex.: `"TOO LATE?"`, `"EMPIRE FALLS"`, `"THE WRONG BET"`), usando fundo de contraste e a cor dourada para a palavra principal. Título e capa devem entregar a promessa comprovada pelo roteiro;
  - **Resolução e arquivo**: Composição horizontal 16:9, referência `1280x720`, em PNG ou JPG de alta qualidade. Salvar uma capa própria por episódio em `public/assets/images/` e indicar o caminho no JSON do episódio; o documentário BlackBerry usa `public/assets/images/blackberry-thumbnail.png`.

---

## 6. Fluxo de Produção e Entrega na Nuvem
1. **Início manual**: A produção começa com o pedido do usuário neste chat/Codex ou no Antigravity. Não criar cron, rotina de notícias ou publicação autônoma por inferência.
2. **Autoria com liberdade**: Dentro do episódio autorizado, o agente pesquisa, escreve, escolhe e prepara mídias, cria imagens de apoio e capa e conduz a produção sem pedir aprovação a cada etapa. Resolver escolhas editoriais e de montagem com julgamento próprio, respeitando as orientações explícitas da conversa.
3. **Fonte única**: O episódio completo é salvo em `episodes/<episodio>.json`, com narração por cena, atos, referências de mídia, fontes e caminho da capa. Arquivos destinados ao renderer são derivados dessa fonte; o antigo piloto de 14 segundos é apenas uma demonstração técnica.
4. **Voz e montagem**: A voz usa Gemini 3.8 Live, Charon e calibração de **-1 semitom**, preservando o tempo. A montagem acompanha as durações reais dos áudios, incluindo toda a fala. O mínimo de duração não pode ser cumprido com padding ou repetição.
5. **Produção na nuvem**: Síntese, preparação pesada e render rodam no **GitHub Actions** (`.github/workflows/render-documentary.yml`), preservando a máquina do usuário. Acompanhar a execução, corrigir falhas concretas e aproveitar áudio já válido quando a alteração for somente visual.
   - **Identificação da execução**: Ao iniciar um episódio, preencher `episode_title` com o nome do tema ou título do vídeo para identificá-lo na lista do GitHub Actions. O nome da execução inclui esse texto e seu número; na ausência do título, usa o caminho do episódio.
   - **Blocos técnicos dinâmicos**: O áudio completo determina a timeline; criar quantos blocos de vídeo forem necessários, independentes dos quatro atos, com até quatro workers simultâneos. O tamanho de referência de cada bloco não limita a duração do episódio. Renderizar uma única mixagem contínua e incorporá-la ao vídeo unido; não dividir o AAC por blocos. Preservar blocos válidos para recuperação de falhas. Alterações futuras não devem cancelar nem reiniciar uma execução em andamento.
6. **Entrega somente ao Drive**: O fluxo envia à pasta do Google Drive:
   - `documentary_final.mp4` (Vídeo Full HD 1080p);
   - a capa própria do episódio, em PNG ou JPG;
   - `youtube_package.txt` (Título + Descrição estruturada + Capítulos/Timestamps reais + Tags + Fontes e créditos utilizados).
7. **Conclusão**: Confirmar os arquivos entregues e informar o link da pasta. **A publicação no YouTube é manual**, feita pelo usuário; este fluxo não faz upload nem publicação automática no YouTube.

### Simplicidade operacional
- Aproveitar do O Dinheiro Explica a clareza da explicação, a pesquisa e a direção visual. **Não importar seus gates editoriais, contratos estruturados, preflights, auditorias obrigatórias ou ciclos de aprovação** para o Plotquake.
- Manter apenas proteções automáticas essenciais à entrega: fala completa e sem corte, consistência das durações de áudio/vídeo, arquivos necessários presentes e íntegros, e confirmação do envio ao Drive. Qualquer problema concreto deve ser corrigido e relatado.
- Pesquisa e cuidado factual fazem parte da autoria. Não transformar escolhas criativas, cadência, estrutura dos atos ou revisão de uma capa em barreiras automáticas adicionais. Informar limites reais de verificação sem inventar aprovação ou resultado.

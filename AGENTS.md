# Plotquake ⚡ - Canal Dark de Documentários (Diretrizes Canônicas para Agentes e IAs)

Este documento é a instrução mandatória e guia mestre do canal **Plotquake**. Qualquer agente de IA ou assistente que atue neste repositório deve ler e seguir estritamente as regras abaixo.

---

## 1. O que é o Plotquake?
- **Conceito**: Canal dark de documentários cinematográficos de alta retenção (15 a 20 minutos) focado na ascensão, guerras corporativas, tecnologias disruptivas e quedas catastróficas de grandes impérios e marcas (*"Plot twists that shake empires"*).
- **Idioma**: **Inglês nativo (US English)**, voltado exclusivamente para a audiência dos países Tier-1 com o maior CPM do mundo (Estados Unidos, Reino Unido, Canadá e Austrália).
- **Referências de Sucesso**: *The Mega-Brands That Built America (History Channel)*, *MagnatesMedia*, *ColdFusion*, *Fern*, *Moon*.

---

## 2. Identidade Visual e Paleta de Cores
- **Cor Primária de Assinatura**: **Laranja Plotquake (`#FF5500` / `#FF6B00`)**. Representa alerta sísmico, perigo, calor e energia de ruptura.
- **Cores de Suporte**:
  - Fundo: Preto/Grafite Cinematográfico Profundo (`#030712` / `#080B11`);
  - Texto Primário: Branco Puro (`#FFFFFF`) e Branco Suave (`#F8FAFC`);
  - Texto Secundário: Slate/Cinza Neutro (`#94A3B8`);
  - Destaques de Contraste: Azul Corporativo (`#3B82F6`) e Dourado/Âmbar (`#F59E0B`).
- **Resolução e Formato**: **Full HD Horizontal (`1920x1080`) a 30 FPS**.
- **Componentes Oficiais Remotion** (em `src/components/`):
  1. `KenBurnsImage`: Zoom suave (in/out) de 1.0 a 1.15, pan, vinheta escura, textura sutil de filme e lower-third documental.
  2. `NewspaperPop`: Jornal de época texturizado com rotação, manchete em caixa alta e marcação em marca-texto amarelo animado nas frases de choque.
  3. `MarketChart`: Gráficos animados de barras mostrando disputa de fatia de mercado (*market share*).
  4. `QuoteCard`: Cartão com citação de CEOs e figuras históricas, com ano e cargo em destaque.
  5. `BrollPlayer`: Player de clipes de arquivo reais (cinemascope 2.39:1, granulação e badge de acervo histórico em laranja).
  6. `ActMarker`: Cartões de transição sísmica que abrem cada um dos 4 atos com linhas de grade e tipografia monumental.

---

## 3. Roteiro e Estrutura Narrativa (Storytelling em 4 Atos)
Nenhum documentário do Plotquake é uma aula acadêmica chata; é um **duelo dramático de poder e dinheiro**.

### A Estrutura dos 4 Atos:
- **Gancho Inicial (Primeiros 5 a 10 segundos)**: Choque factual ou quebra violenta de expectativa. Nunca comece com "Hello guys" ou apresentações burocráticas.
- **Ato 1: O Império e o Monopólio (00:00 - 04:00)**: O auge do poder. A invenção genial, os fundadores bilionários e a crença de que eram intocáveis.
- **Ato 2: A Semente da Queda / O Conflito Invisível (04:00 - 09:00)**: Uma aposta arriscada, a chegada de um rival improvável ou a arrogância executiva.
- **Ato 3: O Ponto de Ruptura / O Duelo de Titãs (09:00 - 15:00)**: O lançamento que muda as regras do jogo. A tentativa desesperada de reação e os erros milionários.
- **Ato 4: O Colapso e a Lição Histórica (15:00 - 20:00)**: A perda de bilhões, a saída dos fundadores e o legado do terremoto na história.

### Ritmo Visual:
- **Cadência de micro-beats**: Nenhuma cena, imagem ou gráfico pode ficar estático por mais de **4 a 5 segundos**. Toda virada de frase pede uma mudança de câmera, recorte de jornal ou novo foco visual.

---

## 4. Voz e Narração (Gemini 3.8 Live)
- **Motor Canônico**: **Gemini 3.8 Live** (`google-genai` SDK WebSocket).
- **Voz Canônica**: Estritamente **Masculina** (**Charon** como padrão oficial ou **Fenrir**) em inglês.
- **Calibração Tonal Grave**: Configurado para soar **pouca coisa mais grave que o padrão** (-1.0 semitom de afinação) com ressonância barítona de peito e dicção cinematográfica de "voz de autoridade/voz de cinema". O script `worker/synthesize_narration.py` aplica automaticamente a instrução vocal no Gemini Live e calibra o tom via FFmpeg preservando o tempo e a naturalidade milimétrica do áudio.
- **Estilo de Entrega**: Narrador sério, dramático, pausado e autoritário (estilo locutor de documentários do History Channel/Netflix). Pausas dramáticas antes de números astronômicos e revelações de enredo.
- **Trilha Sonora**: Base de tensão contínua em sub-graves (*tension drone*) em `public/assets/audio/tension_score.wav` somada a efeitos sonoros pontuais.
- **Regra**: Nunca use sintetizadores básicos de sistema operacional (como Windows SAPI) para produções oficiais.

---

## 5. Engenharia da Capa (Thumbnail de Altíssimo CTR)
- **REGRA DE OURO**: **NUNCA use um frame aleatório extraído do vídeo para a capa!** A capa é uma peça de arte independente e autoral feita sob medida.
- **Conceito Visual**:
  - **Protagonista em Chiaroscuro**: Rosto expressivo de figura histórica/executiva ou silhueta misteriosa com iluminação dramática;
  - **Luz e Atmosfera Laranja**: Brilho de borda (*rim light*) no **Laranja Plotquake (`#FF5500`)** com fundo escuro e esfumaçado;
  - **Micro-Copy de 2 a 3 Palavras**: Letras gigantes em caixa alta (ex.: `"THE $50B MISTAKE"`, `"EMPIRE FALLS"`, `"SECRET CALL"`), usando fundo de contraste e a cor laranja para a palavra de maior choque;
  - **Resolução**: `1280x720` (16:9), formato JPG de alta qualidade, salva em `public/assets/images/thumbnail_concept.jpg`.

---

## 6. Fluxo de Produção e Entrega na Nuvem
1. O roteiro é salvo estruturado em `episodes/` ou em `src/episodes/pilotEpisode.ts`.
2. A voz é sintetizada via `python worker/synthesize_narration.py` com Gemini 3.8 Live (com calibração grave barítona).
3. O render roda no **GitHub Actions** (`.github/workflows/render-documentary.yml`) sem consumir a máquina do usuário.
4. O script `worker/upload_outputs_to_drive.py` faz o upload automático na pasta do Google Drive com:
   - `documentary_final.mp4` (Vídeo Full HD 1080p);
   - `thumbnail.jpg` (Arte oficial dedicada);
   - `youtube_package.txt` (Título de alto CTR + Descrição estruturada + Capítulos/Timestamps + Tags).

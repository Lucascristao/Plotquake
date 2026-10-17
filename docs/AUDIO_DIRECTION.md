# Direção de áudio do Plotquake

Por orientação do usuário, a música usa a técnica do motor de **O Dinheiro Explica**, adaptada à narrativa de cada documentário. Isso não muda Charon, US English ou a calibração de −1 semitom e não importa seus fluxos de aprovação/editoriais.

## Música que conduz a história

`worker/generate_documentary_score.py` produz uma composição instrumental procedural original: progressões harmônicas, pads estéreo discretos, baixo pulsado e plucks/arpejos com presença nos médios. Não depende de Fal, API musical, faixas externas ou samples. O som não deve ser apenas um drone de subgraves nem repetir a mesma intensidade durante todo episódio.

Escolher arcos musicais conforme o conteúdo. Os perfis herdados são `finance` (108 BPM, Dm9/Bbmaj7/Gm7/C9sus4), `market` (114 BPM, Am7/Fmaj9/Dm7/Gsus4), `alert` (104 BPM, Em/Cmaj7/Am9/Bm7) e `personal_finance` (106 BPM, Gmaj7/Em9/Cmaj7/D9sus4). Os nomes são identificadores técnicos; um documentário não precisa repetir esses quatro climas, ordem ou quantidade de segmentos.

Na fonte do episódio, configuração opcional:

```json
{
  "score": {
    "engine": "ode-procedural-v1",
    "volume": 0.72,
    "segments": [
      {"fromScene": "bb-01", "throughScene": "bb-01", "profile": "alert", "gain": 1.0, "pluck": 0.55},
      {"fromScene": "bb-03", "throughScene": "bb-40", "profile": "finance", "gain": 1.0, "pluck": 0.8}
    ]
  }
}
```

Esse exemplo documenta o formato, não a direção definitiva do BlackBerry. Resolver os trechos pela timeline medida dos WAVs reais. `fromScene` e `throughScene` são inclusivos; os segmentos precisam cobrir essa timeline sem buracos/sobreposição. Para silêncio deliberado, usar `gain: 0`. Sem configuração, o gerador usa um único perfil `finance`; a autoria deve escolher variações quando a história pedir.

- `gain` controla somente o áudio sintetizado do segmento, uma vez. Padrão 1.
- `pluck` controla a atividade/intensidade do arpejo, uma vez. Padrão 1.
- `score.volume` é ganho de playback do **mixer final**, padrão 0,72. O gerador registra esse valor no manifesto e **não o aplica ao WAV**. Não multiplicar volume novamente em cada cena.

O arranjo cresce e relaxa ao longo dos segmentos. Transições entre segmentos usam crossfade suave de 2 segundos, reduzido somente em trechos técnicos muito curtos. Acordes e ataques têm suavização para evitar estalos. Não reiniciar música a cada foto, cena, bloco técnico ou chunk de escrita.

## Duração, memória e procedência

```powershell
python worker/generate_documentary_score.py --episode episodes/blackberry.json --timeline out/render-input.json --output public/assets/audio/blackberry-touchscreen-revolution-score.wav
```

Aceita timeline direta ou envolvida em `{"episode": ...}`. A saída é PCM16 estéreo a 48 kHz com número exato de amostras correspondente aos frames medidos. A escrita usa blocos de 8 segundos, com teto interno de 16 segundos, mantendo o relógio absoluto de amostras: memória não cresce com os minutos do vídeo. A mesma fonte/timeline/engine e ID geram PCM determinístico independentemente do tamanho dos blocos de escrita.

O `.json` ao lado do WAV registra duração, amostras, segmentos, RMS/pico, hash do PCM, procedência e separação do ganho de playback. `--test-duration 12` permite um pequeno experimento técnico, explicitamente marcado no manifesto. Esse limite nunca deve entrar no comando de produção. Dependência: `numpy>=1.26`.

A adaptação parte de `worker/generate_music.py` e da técnica de reprodução de `video/src/DailyEditorial.tsx` do repositório do usuário O Dinheiro Explica, inspecionado somente leitura. Não reutiliza como loop o WAV de uma pauta anterior nem atribui uma licença externa inexistente ao material próprio.

## Voz, pausas e efeitos

O O Dinheiro Explica usa referência comum de fala ativa em −18 dBFS, nível musical de playback 0,72 e efeitos pontuais em acontecimentos sincronizados à voz. Seu código inspecionado **não implementa ducking nem subida automática durante pausas internas**. O envelope de pausas é melhoria do mixer do Plotquake, separada deste sintetizador.

`worker/prepare_audio_direction.py` implementa essa preparação sobre o relógio real:

```powershell
python worker/prepare_audio_direction.py --episode episodes/blackberry.json --timeline out/render-input.json --score public/assets/audio/blackberry-touchscreen-revolution-score.wav --output public/assets/audio/blackberry-touchscreen-revolution-score-directed.wav
```

O script mede os WAVs originais em janelas de 20 ms, calcula RMS de fala ativa acima de −45 dBFS e acrescenta `audioGain` a cada cena da timeline derivada. Todas recebem o mesmo alvo de −18 dBFS, reduzido em conjunto quando necessário para não ultrapassar pico 0,86 e conservar espaço na mixagem. Nenhum WAV de voz é regravado, comprimido, cortado ou transposto; hashes antes/depois comprovam preservação. Rodar novamente calcula o ganho a partir dos originais, sem multiplicar o resultado anterior.

As pausas são detectadas pelo PCM, usando limiar de máximo entre −45 dBFS e RMS ativo da cena menos 24 dB. Interrupções de até 0,15 segundo entre trechos ativos são fechadas. Somente silêncios de pelo menos 0,70 segundo recebem elevação. A música começa a subir 0,12 segundo após a última atividade, sobe/desce com rampas suaves de até 0,25 segundo e volta ao nível normal pelo menos 0,16 segundo antes da próxima fala. O multiplicador padrão é 1,6; `score.pauseLift` aceita 1 a 2, e `score.pauseMinimumSeconds` pode exigir pausas maiores que 0,70 segundo. Detecção por energia identifica atividade sonora, não compreende o significado de uma revelação.

O WAV direcionado é estéreo 48 kHz, com duração exata e escrita em blocos de 8 segundos. Já contém `score.volume` aplicado **uma única vez**, além do envelope das pausas; não recebe outro fade global. A timeline é atualizada com `audio.music = {src, volume: 1, loop: false, directed: true}`, removendo cues antigos de volume por cena. O renderer deve respeitar `audioGain` e, para música `directed`, pular o multiplicador antigo de silêncio 1,22 e fades adicionais que duplicariam os do gerador. O relatório `.json` adjacente registra ganhos, picos, pausas, integridade e limites de verificação; não representa audição humana.

Reaproveitar WAVs válidos, sem aplicar novamente a transposição tonal. Equalização de nível e bordas suaves pertencem ao master derivado; os originais permanecem preservados. A música deve continuar perceptível em alto-falantes pequenos, sem cobrir palavras. Subidas nas pausas precisam ser suaves e motivadas por revelação, mudança ou consequência; não bombear a cada respiração. O ganho 0,72 é referência para este sintetizador, não garantia universal de equilíbrio.

Efeitos pontuais devem acompanhar ações/evidências e não toda troca de mídia. Escutar trechos representativos da voz com a música, incluindo uma pausa e uma passagem intensa, antes do render longo. A avaliação precisa incluir volume normal em celular/mono e fones. Medir RMS e integridade ajuda; não comprova sozinho que a trilha acompanha a história.

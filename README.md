![Imagem](https://drive.google.com/uc?export=view&id=1Ejo9FYXsSbWzJuHQzMLfBdBIgsO-8Upg)

# Knowball - módulo de IA para Análise de Sentimento (Sprint 4)

## Visão Geral

Esse módulo implementa uma solução de IA para análise de sentimento em denúncias de arbitragem do sistema Knowball. A pipeline processa relatos em português, classifica o sentimento (Negative / Neutral / Positive), atribui um score de confiança e gera automaticamente o SQL necessário para atualizar a aplicação Oracle APEX - incluindo o campo de status da denúncia.

***

## Estrutura da aplicação

```
knowball-iot/
├── nlp_analyzer.py       ← Script principal de análise NLP
├── apex_updates.sql      ← Gerado automaticamente pelo script (UPDATE statements)
├── knowball_nlp.log      ← Log completo de todas as execuções
```

***

## Requisitos e Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Acesso ao Oracle APEX (workspace `knowball_iot`)

### Instalação das dependências

```bash
pip install textblob deep-translator
python -m textblob.download_corpora
```

### Dependências detalhadas

| Biblioteca | Versão mínima | Finalidade |
|---|---|---|
| `textblob` | 0.17+ | Análise de sentimento em inglês via léxico NLTK |
| `deep-translator` | 1.9+ | Tradução automática PT→EN via Google Translate |
| `unicodedata` | built-in | Normalização de texto (remoção de acentos) |
| `logging` | built-in | Registro de execuções em arquivo e console |
| `sys` | built-in | Leitura de argumentos via linha de comando |
| `datetime` | built-in | Timestamp nas saídas SQL e logs |

***

## Modelo de IA - Pipeline Híbrido

### Arquitetura

O modelo utiliza uma pipeline híbrida de três etapas que combina análise léxica de domínio com processamento de linguagem natural generalista:

![Imagem](https://drive.google.com/uc?export=view&id=1bM5y-zlRJqbcgHxGJkpG6voz0zxHx-SO)

### Léxico de Domínio (Português)

O dicionário léxico foi construído especificamente para o contexto de arbitragem esportiva, com três categorias de termos:

**Exemplo de Termos Negativos** (indicadores de irregularidade):

| Categoria | Exemplos | Peso |
|---|---|---|
| Manipulação direta | `manipulou`, `fraudulento`, `fraude` | 3.5 |
| Padrão de reincidência | `terceira vez`, `sempre o mesmo`, `não pode ser coincidência` | 3.0–3.5 |
| Intencionalidade | `intencional`, `deliberado`, `deliberada` | 3.0 |
| Prejuízo ao time | `prejudicou`, `favoreceu`, `beneficiou` | 2.5 |
| Decisões indevidas | `inexistente`, `indevida`, `ilegítimo` | 2.5–3.0 |
| Termos gerais de irregularidade | `suspeito`, `parcial`, `tendencioso` | 2.0 |

**Exemplo de Termos Positivos** (indicadores de boa arbitragem):

| Categoria | Exemplos | Peso |
|---|---|---|
| Elogio direto | `parabenizar`, `excelente`, `imparcial` | 2.5 |
| Qualidade da condução | `bem apitada`, `bem conduzida`, `fluiu bem` | 2.5 |
| Caracterização justa | `justo`, `correto`, `transparente`, `competente` | 2.0 |

**Intensificadores** (multiplicam o peso dos termos):

| Termo | Fator |
|---|---|
| `extremamente` | 1.7× |
| `claramente`, `completamente`, `obviamente` | 1.5× |
| `muito`, `diretamente` | 1.3–1.4× |

> O fator de intensificação é cumulativo e limitado a no máximo 3.0×.

### Cálculo da Polaridade

A polaridade léxica é calculada pela fórmula:

```
polarity = ((score_pos - score_neg) / total) × min(total / 5.0, 1.0)
```

Onde `total = score_neg + score_pos` após aplicação dos intensificadores. O resultado varia de -1.0 (totalmente negativo) a +1.0 (totalmente positivo).

### Fusão dos Modelos

A decisão de fusão segue a seguinte lógica:

```python
if abs(pol_lexico) > 0.15 ou tradução falhou:
    polarity = pol_lexico          # léxico domina (contexto específico)
else:
    polarity = pol_lexico × 0.70 + pol_textblob × 0.30   # fusão ponderada
```

Esta abordagem prioriza o léxico de domínio quando ele detecta sinais fortes, e usa o TextBlob como complemento para textos ambíguos ou neutros.

### Classificação Final

| Faixa de Polaridade | Sentimento | STATUS no APEX |
|---|---|---|
| `polarity < -0.05` | `Negative` | `Em análise` |
| `-0.05 ≤ polarity ≤ 0.05` | `Neutral` | `Em análise` |
| `polarity > 0.05` | `Positive` | `Concluída` |

O score de confiança (0.00–0.99) é calculado proporcionalmente à intensidade da polaridade:

```
score = 0.55 + (|polarity| - 0.05) × (0.44 / 0.95)
```

## Extração de Entidades

O script extrai automaticamente entidades do texto relacionadas a eventos e ações de arbitragem:

**Tipo `Event`** — lances e situações de jogo:
`penalti`, `falta`, `gol`, `cartao`, `impedimento`, `acrescimo`, `expulsao`, `lance`, `marcacao`

**Tipo `Action`** — verbos de ação do árbitro:
`ignorou`, `marcou`, `anulou`, `beneficiou`, `prejudicou`, `favoreceu`, `errou`, `manipulou`, `permitiu`, `simulou`

As entidades são retornadas com `text`, `type`, `offset` e `length`, simulando o formato de resposta do OCI Language API.

***

## Modos de Uso

### Modo 1 — Análise com protocolo (gera SQL)

```bash
python nlp_analyzer.py "Texto do relato" KNB-023
```

Analisa o texto, exibe o resultado no terminal e **gera/atualiza o arquivo `apex_updates.sql`** com o UPDATE correspondente.

**Exemplo de saída no terminal:**
```
============================================================
  RETORNO OCI LANGUAGE (simulado via NLP v6)
============================================================
  Protocolo: KNB-023
  Sentimento: [NEGATIVO] Negative
  Score NLP: 0.97
  Scores: Negative=0.97 | Neutral=0.02 | Positive=0.01
  Metodo: Lexico PT (dominio)
  STATUS: Em análise
  Entidades: pênalti, marcou
============================================================
```

**Exemplo do SQL gerado em `apex_updates.sql`:**
```sql
-- Gerado em 2026-05-19 08:00:00 pelo nlp_analyzer.py
UPDATE KB_DENUNCIAS
SET SENTIMENTO_OCI = 'Negative',
    SCORE_NLP      = 0.97,
    STATUS         = 'Em análise',
    DT_ATUALIZACAO = SYSDATE
WHERE PROTOCOLO = 'KNB-023';
COMMIT;
```

### Modo 2 — Análise sem protocolo (apenas visualização)

```bash
python nlp_analyzer.py "Texto do relato"
```

Analisa o texto e exibe o resultado, mas **não gera SQL**. Útil para testar o modelo antes de aplicar no banco.

### Modo 3 — Demo automática (5 casos de teste)

```bash
python nlp_analyzer.py
```

Executa os 5 casos de teste pré-configurados e exibe um resumo final com sentimento e score de cada um. SQL **não é gerado** neste modo.

***

## Fluxo de Integração APEX

O mecanismo de integração entre o script Python e o Oracle APEX segue o seguinte fluxo:

![Imagem](https://drive.google.com/uc?export=view&id=1PYleqzHFUZr0na4_49KW9CHiQ1DLZT4a)

### Passo a passo de integração

1. **Registrar denúncia** no formulário APEX (Página 2) e anotar o protocolo gerado (ex: `KNB-023`)

2. **Executar o script** informando o relato e o protocolo:
```bash
   python nlp_analyzer.py "Relato completo da denúncia aqui" KNB-023
```

3. **Abrir o arquivo** `apex_updates.sql` gerado na mesma pasta do script

4. **Copiar o conteúdo** e colar no **SQL Workshop → SQL Commands** do Oracle APEX

5. **Clicar em Run** - o banco é atualizado com sentimento, score e novo status

6. **Consultar denúncia** - o badge NLP e o status atualizado aparecem para o usuário

### Execução em lote (múltiplas denúncias)

Como o arquivo `apex_updates.sql` é **acumulativo**, é possível processar várias denúncias seguidas e aplicar todas de uma vez:

```bash
python nlp_analyzer.py "Relato 1..." KNB-021
python nlp_analyzer.py "Relato 2..." KNB-022
python nlp_analyzer.py "Relato 3..." KNB-023
```

O arquivo conterá os 3 UPDATEs. Cole tudo no SQL Commands e execute uma única vez.

***

## Aplicação Oracle APEX - Telas e Funcionalidades

### Tela Home (Página 1)
Página inicial da aplicação com acesso às funcionalidades de registro de denúncias e consulta por protocolo. Apresenta o branding do sistema Knowball com as cores institucionais (cinza escuro, vermelho e branco);

![Imagem](https://drive.google.com/uc?export=view&id=1jl9KdP2qG0OavF5ti9iP5ko22Yq4Z6nB)

### Tela Registrar Denúncia (Página 2)
Formulário de cadastro da denúncia com os campos:
- **Nome do árbitro** - árbitro alvo da denúncia
- **Relato** - descrição detalhada da ocorrência
- **ID da partida** - identificador da partida referenciada

![Imagem](https://drive.google.com/uc?export=view&id=1qByk9LlRtsXpyLpju8KjdTZs_iurRyM-)

Ao submeter, o sistema gera automaticamente o protocolo no formato `KNB-XXX` via sequence Oracle e redireciona para a tela de confirmação exibindo o número do protocolo gerado.

![Imagem](https://drive.google.com/uc?export=view&id=1nAAr186F4B66xVCfgxeCiK3g2mzI47Lk)

### Tela Consultar Denúncia (Página 4)
Permite ao usuário consultar o status de uma denúncia informando o protocolo. Exibe:
- Dados completos da denúncia (árbitro, relato, data de registro)
- **Status atual** (`Recebida`, `Em análise` ou `Concluída`)
- **Badge de sentimento NLP** com o resultado da análise (`Negative`, `Neutral`, `Positive`) e o score de confiança
- Data da última atualização pela IA

![Imagem](https://drive.google.com/uc?export=view&id=1tJFFHbfgIPU6Jp8-2hgA3GXJJE0mJEy1)

### Tela Dashboard Admin (Página 5)
Painel administrativo com visualizações analíticas das denúncias registradas:
- Gráfico de denúncias por árbitro (ranking de reclamações)
- Distribuição por sentimento NLP (Negative / Neutral / Positive)
- Alertas gerados pela análise de padrões (`KB_ALERTAS`)
- Tendências temporais de registros

![Imagem](https://drive.google.com/uc?export=view&id=1soUEil6ePyjONhQFDxftUpqx16AJfnnM)
![Imagem](https://drive.google.com/uc?export=view&id=17APFCdSvxhgHATcTcASR5Syqzv4Z7AaG)
![Imagem](https://drive.google.com/uc?export=view&id=1hDOLtwDS17B1fWnMgp4xisi4i9wR0b8H)
![Imagem](https://drive.google.com/uc?export=view&id=1OLZ4Rvn1ybUmu_sQipAp0O0OqjEBUKa7)


***

## Observações Técnicas

- O arquivo `apex_updates.sql` é acumulativo. Para reiniciar as evidências de uma nova apresentação, basta deletar ou renomear o arquivo antes de executar o script.
- O arquivo de log `knowball_nlp.log` também é acumulativo e registra todas as execuções com timestamp, útil para demonstrar rastreabilidade.
- A normalização de texto (função `normalizar()`) remove acentos e converte para minúsculas antes da comparação léxica, evitando falsos negativos por variações de acentuação no input.
- O score máximo possível é `0.99` — o valor `1.0` é reservado para indicar certeza absoluta e não é utilizado para manter margem de calibração do modelo.

## Vídeo Pitch

Segue abaixo o link do vídeo pitch publicado no YouTube (em modo não listado) demonstrando o funcionamento da aplicação:

[Clique aqui para assistir](https://youtu.be/GV4OCUHJgMc?si=zAHgC_PP4cQoIEHs)

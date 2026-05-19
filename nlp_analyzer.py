import sys
import json
import logging
import unicodedata
from datetime import datetime
from deep_translator import GoogleTranslator
from textblob import TextBlob

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("knowball_nlp.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

SQL_OUTPUT_FILE = "apex_updates.sql"

# Mapeamento sentimento -> STATUS (valores exatos do banco)
STATUS_MAP = {
    "Negative": "Em análise",
    "Neutral": "Em análise",
    "Positive": "Concluída",
}

# ── Lexico de dominio em portugues (pesos ponderados) ─────────
LEXICO_NEGATIVO = {
    "inexistente": 3.0, "intencional": 3.0, "manipulou": 3.5,
    "manipulacao": 3.5, "fraudulento": 3.5, "fraude": 3.5,
    "deliberado": 3.0, "deliberada": 3.0,
    "prejudicou": 2.5, "prejudica": 2.5, "prejudicar": 2.5,
    "favoreceu": 2.5, "favorecendo": 2.5, "beneficiou": 2.5,
    "anulou": 2.0, "anulados": 2.0, "simulou": 2.0,
    "ignorou": 2.0, "permitiu": 1.5,
    "injusto": 2.0, "injusta": 2.0, "parcial": 2.0,
    "suspeito": 2.0, "suspeita": 2.0, "irregular": 2.0,
    "irregularidade": 2.5, "tendencioso": 2.0, "tendenciosa": 2.0,
    "questionavel": 1.5, "duvidoso": 1.5, "duvidosa": 1.5,
    "absurdo": 2.0, "absurda": 2.0, "revoltante": 2.5,
    "inadmissivel": 2.5, "covarde": 2.5, "descaso": 2.0,
    "incompetente": 2.0, "incompetencia": 2.0,
    "flagrante": 2.5, "inexplicavel": 2.0,
    "terceira vez": 3.0, "quarta vez": 3.5, "mais uma vez": 2.0,
    "reincidente": 3.0, "consecutiva": 2.0, "novamente": 1.5,
    "sempre o mesmo": 3.0, "padrao": 2.0,
    "nao pode ser coincidencia": 3.5, "coincidencia": 1.5,
    "sem justificativa": 2.5, "sem motivo": 2.5,
    "contra nos": 2.0, "prejudicial": 2.0,
    "forcado": 1.5, "forcada": 1.5,
    "inventado": 2.0, "inventada": 2.0,
    "falso": 2.0, "falsa": 2.0,
    "ilegitimo": 2.5, "ilegitima": 2.5,
    "indevida": 2.5, "indevido": 2.5,
    "incorreta": 2.0, "incorreto": 2.0,
    "erronea": 2.0, "erroneo": 2.0,
}

LEXICO_POSITIVO = {
    "justo": 2.0, "justa": 2.0, "correto": 2.0, "correta": 2.0,
    "imparcial": 2.5, "transparente": 2.0, "competente": 2.0,
    "profissional": 2.0, "bem conduzida": 2.5, "bem apitada": 2.5,
    "bem apitado": 2.5, "equilibrado": 2.0, "equilibrada": 2.0,
    "excelente": 2.5, "otimo": 2.0, "otima": 2.0,
    "parabenizar": 2.5, "elogiar": 2.0, "satisfeito": 1.5,
    "satisfeita": 1.5, "tranquilo": 1.5, "tranquila": 1.5,
    "adequado": 1.5, "adequada": 1.5, "eficiente": 1.5,
    "nenhuma irregularidade": 3.0, "sem problemas": 2.0,
    "fluiu bem": 2.5, "decisoes justas": 3.0,
}

INTENSIFICADORES = {
    "muito": 1.4, "claramente": 1.5, "completamente": 1.5,
    "totalmente": 1.5, "absolutamente": 1.5, "extremamente": 1.7,
    "jamais": 1.3, "nunca": 1.3, "sempre": 1.3,
    "diretamente": 1.3, "obviamente": 1.5, "evidentemente": 1.5,
    "indevidamente": 1.5,
}


def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def calcular_polaridade_lexico(texto):
    texto_norm = normalizar(texto)
    palavras = texto_norm.split()
    n_palavras = max(len(palavras), 1)

    fator = 1.0
    hits_int = []
    for palavra, peso in INTENSIFICADORES.items():
        if palavra in texto_norm:
            fator *= peso
            hits_int.append(palavra)
    fator = min(fator, 3.0)

    score_neg = sum(peso for p, peso in LEXICO_NEGATIVO.items() if p in texto_norm)
    score_pos = sum(peso for p, peso in LEXICO_POSITIVO.items() if p in texto_norm)
    hits_neg = [p for p in LEXICO_NEGATIVO if p in texto_norm]
    hits_pos = [p for p in LEXICO_POSITIVO if p in texto_norm]

    score_neg *= fator
    score_pos *= fator
    total = score_neg + score_pos

    if total == 0:
        polarity = 0.0
        subjectivity = 0.0
    else:
        raw = (score_pos - score_neg) / total
        polarity = round(raw * min(total / 5.0, 1.0), 4)
        subjectivity = round(min((len(hits_neg) + len(hits_pos)) / n_palavras * 15, 1.0), 4)

    detalhes = {
        "hits_negativos": hits_neg,
        "hits_positivos": hits_pos,
        "intensificadores": hits_int,
        "fator": round(fator, 2),
        "score_neg": round(score_neg, 2),
        "score_pos": round(score_pos, 2),
    }
    return polarity, subjectivity, detalhes


def traduzir_para_ingles(texto):
    try:
        traduzido = GoogleTranslator(source="pt", target="en").translate(texto)
        return traduzido, True
    except Exception:
        return texto, False


def classificar_sentimento(polarity, subjectivity):
    if polarity < -0.05:
        score = round(0.55 + (abs(polarity) - 0.05) * (0.44 / 0.95), 2)
        return "Negative", min(score, 0.99)
    elif polarity > 0.05:
        score = round(0.55 + (polarity - 0.05) * (0.44 / 0.95), 2)
        return "Positive", min(score, 0.99)
    else:
        score = round(0.50 + subjectivity * 0.20, 2)
        return "Neutral", min(score, 0.75)


def extrair_entidades(texto_pt):
    entidades = []
    palavras_chave = {
        "Event":  ["penalti", "falta", "gol", "cartao", "impedimento",
                   "acrescimo", "expulsao", "lance", "marcacao"],
        "Action": ["ignorou", "marcou", "anulou", "beneficiou", "prejudicou",
                   "favoreceu", "errou", "manipulou", "permitiu", "simulou"],
    }
    texto_norm = normalizar(texto_pt)
    texto_orig = texto_pt.lower()
    for tipo, palavras in palavras_chave.items():
        for palavra in palavras:
            if palavra in texto_norm and palavra in texto_orig:
                idx = texto_orig.index(palavra)
                entidades.append({
                    "text": texto_pt[idx:idx + len(palavra)],
                    "type": tipo,
                    "offset": idx,
                    "length": len(palavra),
                })
    return entidades[:5]


def gerar_sql(protocolo, sentimento, score):
    if protocolo == "KNB-INPUT":
        return

    novo_status = STATUS_MAP.get(sentimento, "Em análise")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linha = (
        "-- Gerado em " + timestamp + " pelo nlp_analyzer.py\n"
        "UPDATE KB_DENUNCIAS\n"
        "SET SENTIMENTO_OCI = '" + sentimento + "',\n"
        "    SCORE_NLP = " + str(score) + ",\n"
        "    STATUS = '" + novo_status + "',\n"
        "    DT_ATUALIZACAO = SYSDATE\n"
        "WHERE PROTOCOLO = '" + protocolo + "';\n"
        "COMMIT;\n\n"
    )

    with open(SQL_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(linha)

    log.info("=" * 60)
    log.info("SQL gerado -> " + SQL_OUTPUT_FILE)
    log.info("STATUS será atualizado para: '" + novo_status + "'")
    log.info("Cole no SQL Commands do APEX:")
    log.info("-" * 60)
    log.info(linha.strip())
    log.info("=" * 60)


def analisar_relato(protocolo, texto_pt):
    log.info("Analisando relato do protocolo " + protocolo + "...")
    resumo = texto_pt[:80] + "..." if len(texto_pt) > 80 else texto_pt
    log.info("Texto: \"" + resumo + "\"")

    # Passo 1: Lexico PT
    pol_lexico, sub_lexico, detalhes = calcular_polaridade_lexico(texto_pt)
    log.info(
        "Lexico PT — neg: " + str(detalhes["hits_negativos"]) +
        " | fator: " + str(detalhes["fator"]) +
        " | score_neg: " + str(detalhes["score_neg"]) +
        " | score_pos: " + str(detalhes["score_pos"]) +
        " | polarity: " + str(round(pol_lexico, 4))
    )

    # Passo 2: TextBlob EN
    texto_en, traducao_ok = traduzir_para_ingles(texto_pt)
    pol_textblob = 0.0
    sub_textblob = 0.0
    if traducao_ok:
        blob = TextBlob(texto_en)
        pol_textblob = blob.sentiment.polarity
        sub_textblob = blob.sentiment.subjectivity
        log.info("TextBlob EN — polarity: " + str(round(pol_textblob, 4)))

    # Passo 3: Fusao
    if abs(pol_lexico) > 0.15 or not traducao_ok:
        polarity = pol_lexico
        subjectivity = sub_lexico
        metodo = "Lexico PT (dominio)" if traducao_ok else "Lexico PT (fallback SSL)"
    else:
        polarity = round(pol_lexico * 0.70 + pol_textblob * 0.30, 4)
        subjectivity = round(sub_lexico * 0.60 + sub_textblob * 0.40, 4)
        metodo = "Hibrido (Lexico PT 70% + TextBlob EN 30%)"

    log.info("Fusao — " + metodo + " | polarity: " + str(round(polarity, 4)))

    sentimento, score = classificar_sentimento(polarity, subjectivity)

    if sentimento == "Negative":
        scores = {"negative": score, "neutral": round((1 - score) * 0.7, 2), "positive": round((1 - score) * 0.3, 2)}
    elif sentimento == "Positive":
        scores = {"positive": score, "neutral": round((1 - score) * 0.7, 2), "negative": round((1 - score) * 0.3, 2)}
    else:
        scores = {"neutral": score, "negative": round((1 - score) * 0.5, 2), "positive": round((1 - score) * 0.5, 2)}

    entidades = extrair_entidades(texto_pt)

    payload = {
        "documents": [{
            "key": protocolo,
            "sentiment": sentimento,
            "documentScores": scores,
            "polarity_raw": round(polarity, 4),
            "subjectivity": round(subjectivity, 4),
            "metodo_analise": metodo,
            "entities": entidades,
            "analyzedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }]
    }

    # Passo 4: Gera SQL com STATUS atualizado
    gerar_sql(protocolo, sentimento, score)

    return payload


def exibir_resultado(payload):
    doc = payload["documents"][0]
    sentimento = doc["sentiment"]
    score = doc["documentScores"][sentimento.lower()]
    labels = {"Negative": "[NEGATIVO]", "Neutral": "[NEUTRO]", "Positive": "[POSITIVO]"}
    label = labels.get(sentimento, "[?]")
    novo_status = STATUS_MAP.get(sentimento, "Em analise")

    log.info("=" * 60)
    log.info("RETORNO OCI LANGUAGE (simulado via NLP v6)")
    log.info("=" * 60)
    log.info("Protocolo : " + doc["key"])
    log.info("Sentimento: " + label + " " + sentimento)
    log.info("Score NLP : " + str(round(score, 2)))
    neg = doc["documentScores"]["negative"]
    neu = doc["documentScores"]["neutral"]
    pos = doc["documentScores"]["positive"]
    log.info("Scores : Negative=" + str(neg) + " | Neutral=" + str(neu) + " | Positive=" + str(pos))
    log.info("Metodo : " + doc["metodo_analise"])
    log.info("STATUS : " + novo_status)
    if doc["entities"]:
        log.info("Entidades : " + ", ".join(e["text"] for e in doc["entities"]))
    log.info("=" * 60)
    return sentimento, score


def main():
    log.info("=" * 60)
    log.info("KNOWBALL -- Analisador NLP v6")
    log.info("Execucao: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    log.info("SQL de atualizacao salvo em: " + SQL_OUTPUT_FILE)
    log.info("=" * 60)

    # Modo 1: texto + protocolo -> analisa e gera SQL
    if len(sys.argv) >= 3:
        texto = sys.argv[1]
        protocolo = sys.argv[2]
        payload = analisar_relato(protocolo, texto)
        exibir_resultado(payload)
        return

    # Modo 2: so texto -> analisa sem gerar SQL
    if len(sys.argv) == 2:
        texto = sys.argv[1]
        payload = analisar_relato("KNB-INPUT", texto)
        exibir_resultado(payload)
        return

    # Modo 3: sem argumentos -> 5 casos demo
    casos_demo = [
        ("KNB-001", "O arbitro marcou dois penaltis inexistentes. Parecia intencional para prejudicar nossa equipe."),
        ("KNB-003", "Terceira vez que esse arbitro prejudica nossa equipe. Gols anulados sem justificativa."),
        ("KNB-008", "Decisao polemica no final, mas pode ter sido erro sem intencao."),
        ("KNB-010", "Partida bem apitada. As decisoes foram justas e o jogo fluiu bem."),
        ("KNB-013", "Terceira partida com decisoes que favorecem o mesmo time. Nao pode ser coincidencia."),
    ]

    log.info("Modo demo — SQL nao sera gerado\n")
    resultados = []
    for protocolo, texto in casos_demo:
        payload = analisar_relato(protocolo, texto)
        sent, score = exibir_resultado(payload)
        resultados.append((protocolo, sent, score))

    log.info("\n===== RESUMO =====")
    labels = {"Negative": "[NEGATIVO]", "Neutral": "[NEUTRO]", "Positive": "[POSITIVO]"}
    for protocolo, sent, score in resultados:
        novo_status = STATUS_MAP.get(sent, "Em analise")
        log.info("  " + protocolo + ": " + labels.get(sent, "") + " " + sent + " -> STATUS: " + novo_status + " (" + str(round(score, 2)) + ")")

    log.info("\nLog: knowball_nlp.log")


if __name__ == "__main__":
    main()
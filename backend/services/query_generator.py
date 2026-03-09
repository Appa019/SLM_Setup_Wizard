# backend/services/query_generator.py
from openai import AsyncOpenAI
from config import settings
from services.cost_tracker import record
from utils.json_extract import extract_json_array

QUERY_PROMPT = """Voce e um especialista em curadoria de dados para fine-tuning de LLMs.
Sua tarefa e gerar exatamente {count} queries de busca altamente especificas para coletar dados de treinamento.

Perfil do dominio (extraido de conversa com o usuario):
- Area principal: {area}
- Subtopicos: {subtopics}
- Termos-chave e jargoes: {keywords}
- Profundidade alvo: {depth}
- Fontes preferidas: {sources}
- Tom esperado do modelo: {tone}
- Resumo do perfil: {summary}

Regras OBRIGATORIAS:
- Gere queries que retornem conteudo ESPECIFICO para treinar um modelo nesse dominio
- Misture queries em portugues e ingles (60% PT, 40% EN)
- Inclua variações de: perguntas tecnicas, tutoriais, documentacao oficial, estudos de caso, exemplos praticos, jargoes do setor
- Priorize queries que retornem conteudo denso em conhecimento (nao noticias genericas)
- Cada query deve ser distinta — sem parafrasear queries anteriores
- Adapte a profundidade das queries ao nivel: {depth}
- Retorne APENAS um JSON array de strings, sem texto adicional

Exemplo de formato:
["query especifica 1", "query especifica 2"]"""


BATCH_SIZE = 50  # GPT-4o-mini is reliable up to 50 queries per call


async def _call_once(client: AsyncOpenAI, prompt: str) -> list[str]:
    """Single API call; returns parsed query list (may be empty on failure)."""
    response = await client.responses.create(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": prompt}],
        max_output_tokens=10000,
    )
    usage = getattr(response, "usage", None)
    if usage:
        record("gpt-4o-mini", "other",
               getattr(usage, "input_tokens", 0),
               getattr(usage, "output_tokens", 0))
    text = ""
    for item in response.output:
        if getattr(item, "type", "") == "message":
            for block in item.content:
                if getattr(block, "type", "") == "output_text":
                    text = block.text
                    break
    result = extract_json_array(text)
    return [str(q) for q in result if q] if isinstance(result, list) else []


async def generate_queries(topic_profile: dict, count: int = 50) -> list[str]:
    """Generates `count` search queries using batches of 50 to ensure reliability."""
    area      = topic_profile.get("area", "")
    keywords  = topic_profile.get("keywords", [])
    subtopics = topic_profile.get("subtopics", [])
    depth     = topic_profile.get("depth", "intermediario")
    sources   = topic_profile.get("sources", [])
    tone      = topic_profile.get("tone", "tecnico e objetivo")
    summary   = topic_profile.get("summary", "")

    if not area and not keywords:
        return list(keywords)

    fallback = list(keywords) + ([area] if area else [])

    base_vars = dict(
        area=area,
        subtopics=", ".join(subtopics) if subtopics else "nao especificado",
        keywords=", ".join(keywords) if keywords else "nao especificado",
        depth=depth,
        sources=", ".join(sources) if sources else "variado",
        tone=tone,
        summary=summary or "nao especificado",
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        collected: list[str] = []
        remaining = count
        MAX_ITERS = 10
        no_progress = 0

        while remaining > 0 and no_progress < 3:
            batch = min(remaining, BATCH_SIZE)
            # Tell the model to avoid repeating already collected queries
            exclusion = (
                f"\n\nNao repita nenhuma dessas queries ja geradas:\n{collected}"
                if collected else ""
            )
            prompt = QUERY_PROMPT.format(count=batch, **base_vars) + exclusion
            batch_result = await _call_once(client, prompt)
            if not batch_result:
                break  # model failed, stop
            # Deduplicate against already collected
            new_queries = [q for q in batch_result if q not in collected]
            if not new_queries:
                no_progress += 1
                continue
            no_progress = 0
            collected.extend(new_queries)
            remaining -= len(new_queries)
            if len(collected) >= MAX_ITERS * BATCH_SIZE:
                break  # safety cap

        if collected:
            return collected[:count]

    except Exception:
        pass

    return fallback

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


async def generate_queries(topic_profile: dict, count: int = 50) -> list[str]:
    """Gera 50 queries de busca expandidas a partir do topic profile."""
    area      = topic_profile.get("area", "")
    keywords  = topic_profile.get("keywords", [])
    subtopics = topic_profile.get("subtopics", [])
    depth     = topic_profile.get("depth", "intermediario")
    sources   = topic_profile.get("sources", [])
    tone      = topic_profile.get("tone", "tecnico e objetivo")
    summary   = topic_profile.get("summary", "")

    # Fallback imediato se não há informação suficiente
    if not area and not keywords:
        return keywords

    fallback = keywords + ([area] if area else [])

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = QUERY_PROMPT.format(
            count=count,
            area=area,
            subtopics=", ".join(subtopics) if subtopics else "nao especificado",
            keywords=", ".join(keywords) if keywords else "nao especificado",
            depth=depth,
            sources=", ".join(sources) if sources else "variado",
            tone=tone,
            summary=summary or "nao especificado",
        )
        response = await client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": prompt}],
            max_output_tokens=2000,
        )
        usage = getattr(response, "usage", None)
        if usage:
            record("gpt-4o-mini", "other",
                   getattr(usage, "input_tokens", 0),
                   getattr(usage, "output_tokens", 0))

        # Extrair texto da resposta
        text = ""
        for item in response.output:
            if getattr(item, "type", "") == "message":
                for block in item.content:
                    if getattr(block, "type", "") == "output_text":
                        text = block.text
                        break

        # Parsear JSON array
        queries = extract_json_array(text)
        if isinstance(queries, list) and queries:
            return [str(q) for q in queries if q]

    except Exception:
        pass

    return fallback

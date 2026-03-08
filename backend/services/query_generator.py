# backend/services/query_generator.py
from openai import AsyncOpenAI
from config import settings
from services.cost_tracker import record
from utils.json_extract import extract_json_array

QUERY_PROMPT = """Voce recebe o perfil de um dominio de conhecimento e deve gerar exatamente 50 queries de busca na web.

Perfil do dominio:
- Area: {area}
- Subtopicos: {subtopics}
- Keywords: {keywords}
- Profundidade: {depth}

Regras:
- Misture queries em portugues e ingles (cerca de 60% PT, 40% EN)
- Varie os formatos: perguntas, termos tecnicos, jargoes, exemplos praticos, tutoriais, documentacao
- Inclua termos especificos do dominio que aparecem em artigos especializados
- Nao repita a mesma query com palavras diferentes
- Retorne APENAS um JSON array de strings, sem texto adicional

Exemplo de formato:
["query 1", "query 2", "query 3"]"""


async def generate_queries(topic_profile: dict) -> list[str]:
    """Gera 50 queries de busca expandidas a partir do topic profile."""
    area      = topic_profile.get("area", "")
    keywords  = topic_profile.get("keywords", [])
    subtopics = topic_profile.get("subtopics", [])
    depth     = topic_profile.get("depth", "intermediario")

    # Fallback imediato se não há informação suficiente
    if not area and not keywords:
        return keywords

    fallback = keywords + ([area] if area else [])

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = QUERY_PROMPT.format(
            area=area,
            subtopics=", ".join(subtopics) if subtopics else "nao especificado",
            keywords=", ".join(keywords) if keywords else "nao especificado",
            depth=depth,
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

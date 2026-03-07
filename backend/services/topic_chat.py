import json
from openai import AsyncOpenAI
from config import settings
from services.cost_tracker import record

SYSTEM_PROMPT = """Voce e um assistente especializado em ajudar usuarios a definir o tema
para fine-tuning de um modelo de linguagem local (LLM).

Seu objetivo e conduzir uma conversa estruturada para extrair:
1. Area principal de conhecimento (ex: direito tributario, medicina veterinaria, programacao Python)
2. Sub-topicos especificos que o modelo deve dominar
3. Nivel de profundidade desejado (basico, intermediario, avancado)
4. Termos-chave e jargoes do dominio
5. Tipos de fontes preferidas (academico, blogs, documentacao tecnica, forums, artigos)
6. Tom e estilo de resposta esperado do modelo

Faca perguntas claras e objetivas. Quando tiver informacao suficiente (geralmente 4-6 trocas),
pergunte se o usuario esta satisfeito para finalizar.

Seja direto e profissional. Nao use emojis excessivos."""

FINALIZE_PROMPT = """Com base na conversa acima, extraia e retorne um JSON estruturado com:
{
  "area": "area principal de conhecimento",
  "subtopics": ["lista", "de", "subtopicos"],
  "depth": "basico|intermediario|avancado",
  "keywords": ["termos", "chave", "para", "scraping"],
  "sources": ["tipos", "de", "fontes"],
  "tone": "descricao do tom esperado",
  "summary": "resumo em 1-2 frases do perfil do modelo"
}"""


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def stream_chat(messages: list[dict]):
    client = get_client()
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        stream=True,
        max_tokens=600,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def finalize_topic(messages: list[dict]) -> dict:
    client = get_client()
    full_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + messages
        + [{"role": "user", "content": FINALIZE_PROMPT}]
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    usage = response.usage
    if usage:
        record("gpt-4o-mini", "chat", usage.prompt_tokens, usage.completion_tokens)
    content = response.choices[0].message.content or "{}"
    return json.loads(content)

import asyncio
import json
import time
from pathlib import Path

from openai import AsyncOpenAI
from config import settings

DATA_RAW = Path(__file__).parent.parent.parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent.parent.parent / "data" / "processed"

preprocess_state: dict = {
    "running": False,
    "total_chunks": 0,
    "done": 0,
    "failed": 0,
    "pairs_generated": 0,
    "finished": False,
    "error": "",
    "examples": [],
}


def get_state() -> dict:
    return dict(preprocess_state)


def _chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += p + "\n\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            current = p + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


SYSTEM_PROMPT = """Voce e um especialista em criacao de datasets para fine-tuning de LLMs.
Dado um trecho de texto, gere 2-3 pares de treinamento no formato JSON com campos:
- instruction: uma instrucao ou pergunta natural em portugues
- input: contexto adicional (pode ser vazio "")
- output: resposta detalhada e precisa baseada no texto

Retorne apenas um array JSON valido. Exemplo:
[{"instruction": "...", "input": "", "output": "..."}]"""


async def _process_chunk(client: AsyncOpenAI, chunk: str, topic: str) -> list[dict]:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Topico: {topic}\n\nTexto:\n{chunk}"},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        content = response.choices[0].message.content or "[]"
        # Extract JSON array from response
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception:
        pass
    return []


async def run_preprocessing(topic_profile: dict):
    global preprocess_state
    preprocess_state.update({
        "running": True, "total_chunks": 0, "done": 0, "failed": 0,
        "pairs_generated": 0, "finished": False, "error": "", "examples": [],
    })

    scraped_file = DATA_RAW / "scraped.jsonl"
    if not scraped_file.exists():
        preprocess_state["error"] = "Arquivo de scraping nao encontrado. Execute o scraping primeiro."
        preprocess_state["running"] = False
        return

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # Read scraped data
    items = []
    with scraped_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass

    # Build chunks
    all_chunks = []
    for item in items:
        text = item.get("text", "")
        chunks = _chunk_text(text)
        all_chunks.extend(chunks[:3])  # Max 3 chunks per page

    preprocess_state["total_chunks"] = len(all_chunks)
    topic_area = topic_profile.get("area", "conhecimento geral")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    all_pairs: list[dict] = []
    sem = asyncio.Semaphore(5)

    async def process_one(chunk: str):
        async with sem:
            pairs = await _process_chunk(client, chunk, topic_area)
            if pairs:
                all_pairs.extend(pairs)
                preprocess_state["pairs_generated"] = len(all_pairs)
                preprocess_state["done"] += 1
                # Store last 5 examples for preview
                preprocess_state["examples"] = all_pairs[-5:]
            else:
                preprocess_state["failed"] += 1

    tasks = [process_one(c) for c in all_chunks]
    await asyncio.gather(*tasks)

    # Save JSONL
    output = DATA_PROCESSED / "training_data.jsonl"
    with output.open("w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    preprocess_state["running"] = False
    preprocess_state["finished"] = True

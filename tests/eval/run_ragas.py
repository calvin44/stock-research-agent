"""
RAG pipeline evaluation using DeepEval.
Measures retrieval and generation quality against a golden test set.

Metrics:
  - Contextual Recall    ← did retriever find the right chunks?
  - Contextual Precision ← are retrieved chunks relevant?
  - Faithfulness         ← is the answer grounded in chunks?
  - Answer Relevancy     ← does the answer address the question?

Run with:
  uv run python tests/eval/run_ragas.py

Requires:
  - Docker Compose running (Qdrant + Postgres)
  - UNTR document already indexed in Qdrant
  - OPENAI_API_KEY set in .env
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, ErrorConfig
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase
from openai import OpenAI

from backend.config import settings  # noqa: F401 — populates os.environ
from backend.rag.retriever import format_chunks_for_llm, retrieve_from_reports

# ── Configuration ─────────────────────────────────────────────────────────────

GOLDEN_SET_PATH = Path("tests/eval/golden_set.json")
RESULTS_PATH = Path("tests/eval/ragas_results.json")
COMPANY = "UNTR"
MODEL = "gpt-4o-mini"

# metric display names → our score keys
METRIC_NAMES = {
    "Contextual Recall": "contextual_recall",
    "Contextual Precision": "contextual_precision",
    "Faithfulness": "faithfulness",
    "Answer Relevancy": "answer_relevancy",
}


# ── Answer generation ─────────────────────────────────────────────────────────


def generate_answer(question: str, context: str) -> str:
    """Generate an answer using the LLM given the question and retrieved context."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial analyst. Answer the question based ONLY "
                    "on the provided context. If the answer is not in the context, "
                    "say 'Informasi tidak tersedia dalam dokumen yang diberikan.' "
                    "Be concise and factual."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


# ── Main evaluation ───────────────────────────────────────────────────────────


def run_evaluation() -> dict:
    """Run DeepEval evaluation against the golden test set."""
    print(f"Loading golden set from {GOLDEN_SET_PATH}...")
    with open(GOLDEN_SET_PATH) as f:
        golden_set = json.load(f)

    golden_set = golden_set[:5]  # limit for initial baseline

    print(f"Loaded {len(golden_set)} questions.")
    print(f"Company:  {COMPANY}")
    print(f"Model:    {MODEL}")
    print("-" * 50)

    test_cases = []

    for i, item in enumerate(golden_set):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"\n[{i + 1}/{len(golden_set)}] {question}")

        # retrieve relevant chunks
        chunks = retrieve_from_reports(
            query=question,
            company=COMPANY,
            top_k_retrieve=20,
            top_k_final=5,
        )

        if not chunks:
            print("  ⚠ No chunks retrieved — skipping")
            continue

        # format context for answer generation (use all chunks)
        context_str = format_chunks_for_llm(chunks)

        # limit to 2 chunks for faithfulness to avoid token limit
        chunk_texts = [chunk.content for chunk in chunks[:2]]

        # generate answer
        answer = generate_answer(question, context_str)
        print(f"  ✓ Retrieved {len(chunks)} chunks")
        print(f"  ✓ Answer: {answer[:100]}...")

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            expected_output=ground_truth,
            retrieval_context=chunk_texts,  # type: ignore[arg-type]
        )
        test_cases.append(test_case)

    print(f"\n\nEvaluating {len(test_cases)} test cases with DeepEval...")
    print("(This makes multiple OpenAI API calls — may take 3-5 minutes)")
    print("-" * 50)

    metrics = [
        ContextualRecallMetric(threshold=0.5, model=MODEL, include_reason=True),
        ContextualPrecisionMetric(threshold=0.5, model=MODEL, include_reason=True),
        FaithfulnessMetric(
            threshold=0.5,
            model="gpt-4o",  # ← gpt-4o required: gpt-4o-mini hits token limit
            include_reason=True,
        ),
        AnswerRelevancyMetric(threshold=0.5, model=MODEL, include_reason=True),
    ]

    results = evaluate(
        test_cases=test_cases,
        metrics=metrics,
        async_config=AsyncConfig(
            run_async=True,
            throttle_value=10,
            max_concurrent=2,
        ),
        error_config=ErrorConfig(
            ignore_errors=True,
        ),
    )

    # aggregate scores per metric
    metric_scores: dict[str, list[float]] = {v: [] for v in METRIC_NAMES.values()}

    for test_result in results.test_results:
        for metric_data in test_result.metrics_data or []:
            metric_key = METRIC_NAMES.get(metric_data.name)
            if metric_key and metric_data.score is not None:
                metric_scores[metric_key].append(metric_data.score)

    # average per metric
    scores: dict[str, float] = {}
    for metric_key, score_list in metric_scores.items():
        scores[metric_key] = round(sum(score_list) / len(score_list), 4) if score_list else 0.0

    return scores


def main():
    scores = run_evaluation()

    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(f"Company:  {COMPANY}")
    print("Document: Lap Perkembangan Usaha 1Q 2026.pdf")
    print(f"Model:    {MODEL}")
    print(f"Date:     {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    print("-" * 50)

    for metric, score in scores.items():
        bar = "█" * int(score * 20)
        status = "✅" if score >= 0.7 else "⚠️" if score >= 0.5 else "❌"
        print(f"{status} {metric:<25} {score:.4f}  {bar}")

    print("-" * 50)
    if scores:
        avg = sum(scores.values()) / len(scores)
        print(f"   {'Average':<25} {avg:.4f}")
    print("=" * 50)

    output = {
        "timestamp": datetime.now(UTC).isoformat(),
        "company": COMPANY,
        "model": MODEL,
        "num_questions": len(scores),
        "scores": scores,
        "framework": "deepeval",
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {RESULTS_PATH}")

    print("\n📊 INTERPRETATION GUIDE")
    print("  contextual_recall:    Did retriever find the right chunks?")
    print("  contextual_precision: Are retrieved chunks relevant (low noise)?")
    print("  faithfulness:         Is answer grounded in chunks (no hallucination)?")
    print("  answer_relevancy:     Does answer address the question?")
    print("\n  Thresholds: ✅ ≥ 0.70  ⚠️ 0.50-0.69  ❌ < 0.50")


if __name__ == "__main__":
    main()

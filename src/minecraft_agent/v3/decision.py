"""Optional fast social decisions. Generation and operational permissions stay separate."""

from __future__ import annotations
import asyncio, json, logging, math, time
import httpx
from .config import Secrets

LOG = logging.getLogger("kei.decision")
QUESTIONS = [
    {
        "type": "choice",
        "name": "intent",
        "instructions": "Classify the CURRENT speaker request using author IDs and reply chains. Work means a legitimate request to inspect or change their assigned server, never nearby discussion. Character irritation never cancels work.",
        "choices": [{"value": "chat"}, {"value": "work"}, {"value": "none"}],
    },
    {
        "type": "choice",
        "name": "action",
        "instructions": "Choose appropriate participation by Kei. Silence for people talking to each other or irrelevant noise; react for an acknowledgment/affection needing no words; reply for a real question or meaningful direct exchange. Read the referenced message, not just the last nearby message.",
        "choices": [{"value": "reply"}, {"value": "react"}, {"value": "silence"}],
    },
    {
        "type": "choice",
        "name": "reaction",
        "instructions": "If a reaction fits, choose a suitable one. Thumbs up is a neutral/playful acknowledgment; heart for warmth, support or affectionate thanks.",
        "choices": [{"value": "👍"}, {"value": "❤️"}],
    },
]


class DecisionBroker:
    def __init__(self, config, secret_store=None):
        self.cfg = config.get("decisions", {})
        self.secrets = secret_store or Secrets(config.get("secrets_file", "data/secrets.json"))

    @property
    def enabled(self):
        return self.cfg.get("provider", "off") in ("openai", "jev")

    async def evaluate(self, state, client=None):
        if not self.enabled:
            return None
        provider = self.cfg["provider"]
        key = self.secrets.get(
            self.cfg.get(
                "key_ref", "env:OPENAI_API_KEY" if provider == "openai" else "env:TYPESAFE_API_KEY"
            )
        )
        if not key:
            return None
        started = time.perf_counter()
        if provider == "openai":
            base = self.cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
            body = {
                "model": self.cfg.get("model", "gpt-6-luna"),
                "input": json.dumps(state, ensure_ascii=False),
                "questions": QUESTIONS,
            }
            endpoint = base + "/decisions"
        else:
            base = self.cfg.get("base_url", "https://api.typesafe.ai/v1").rstrip("/")
            body = {
                "model": self.cfg.get("model", "jev-latest"),
                "state": state,
                "questions": {
                    q["name"]: {
                        "type": "choice",
                        "instructions": q["instructions"],
                        "criteria": {c["value"]: c.get("description") for c in q["choices"]},
                    }
                    for q in QUESTIONS
                },
            }
            endpoint = base + "/systemone"
        own = client is None
        client = client or httpx.AsyncClient(timeout=float(self.cfg.get("timeout", 8)))
        try:
            response = await client.post(
                endpoint, headers={"Authorization": "Bearer " + key}, json=body
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data,dict):raise ValueError('invalid_envelope')
            answers = data.get("answers", {})
            if isinstance(answers, list):
                if not all(isinstance(a,dict) for a in answers):raise ValueError('invalid_answers')
                answers = {a.get("name"): a for a in answers}
            if not isinstance(answers,dict):raise ValueError('invalid_answers')
            out = {}
            for q in QUESTIONS:
                answer = answers.get(q["name"], {})
                if not isinstance(answer,dict):raise ValueError('invalid_answer')
                if answer.get("type") != "choice" or answer.get("choice") not in [
                    c["value"] for c in q["choices"]
                ]:
                    raise ValueError("invalid_or_refused_decision")
                confidence = answer.get("confidence", 0)
                if (
                    isinstance(confidence,bool) or not isinstance(confidence, (float, int))
                    or not math.isfinite(confidence)
                    or not 0 <= confidence <= 1
                ):
                    raise ValueError("invalid_confidence")
                out[q["name"]] = answer["choice"]
                out[q["name"] + "_confidence"] = confidence
            LOG.info(
                "SOCIAL_DECISION provider=%s action=%s intent=%s confidence=%.3f duration_ms=%.1f",
                provider,
                out["action"],
                out["intent"],
                out["action_confidence"],
                (time.perf_counter() - started) * 1000,
            )
            return out
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            LOG.warning(
                "SOCIAL_DECISION_FALLBACK provider=%s error=%s", provider, type(exc).__name__
            )
            return None
        finally:
            if own:
                await client.aclose()

    def decisive(self, decision):
        return bool(
            decision
            and decision["action_confidence"] >= float(self.cfg.get("min_confidence", 0.65))
        )

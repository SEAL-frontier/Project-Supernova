# Fast social decisions / Quyết định xã hội nhanh

Direct chat normally uses one generation call. Ambiguous public participation can use a fast decision first; silence/react needs no generated paragraph. Backend permissions remain authoritative. Dỗi không được chặn việc được giao hợp lệ.

Put one optional provider in your private config:

```yaml
decisions:
  provider: openai
  model: gpt-6-luna
  key_ref: env:OPENAI_API_KEY
  min_confidence: 0.65
  timeout: 8
```

OpenAI uses the official [Decisions API](https://developers.openai.com/api/docs/guides/decisions). Generation still uses your configured chat provider. Or select Jev:

```yaml
decisions:
  provider: jev
  model: jev-latest
  key_ref: env:TYPESAFE_API_KEY
  min_confidence: 0.65
  timeout: 8
```

Jev matches the documented [TypeSafe System One API](https://docs.typesafe.ai/api); no live Jev key was supplied for this release. `provider: off` retains the chat router. Missing credentials, refusals, invalid output and timeouts fall back to it. Confidence is not a correctness guarantee: evaluate thresholds on your own conversations.

Keep keys in environment variables or the server-side secret store. Public persona/env/test placeholders intentionally have no operator values.

The chat/completions client sends `x-9router-token-saver: off`. In a separate OpenCode installation using 9router, put the same header under `provider.<provider>.options.headers`; reload sessions that cache provider configuration.

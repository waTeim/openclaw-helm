{{/* Known provider metadata for iterating. */}}
{{- define "openclaw.authMap" -}}
openai:
  mode: token
  profileId: "openai:default"
  secretKey: openaiApiKey
  envVar: OPENAI_API_KEY
  onboardFlag: --openai-api-key
anthropic:
  mode: token
  profileId: "anthropic:default"
  secretKey: anthropicApiKey
  envVar: ANTHROPIC_API_KEY
  onboardFlag: --anthropic-api-key
openrouter:
  mode: token
  profileId: "openrouter:default"
  secretKey: openrouterApiKey
  envVar: OPENROUTER_API_KEY
  onboardFlag: --openrouter-api-key
gemini:
  mode: token
  profileId: "gemini:default"
  secretKey: geminiApiKey
  envVar: GEMINI_API_KEY
  onboardFlag: --gemini-api-key
{{- end -}}
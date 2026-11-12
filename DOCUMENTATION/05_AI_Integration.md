# AI integration

The citizen-only `POST /api/v1/ai/analyze/` endpoint calls Google Gemini from Django. `GEMINI_API_KEY` is server-side only; no credential is bundled with the frontend. The configured model defaults to `gemini-3.5-flash-lite`. The request uses a bounded 30-second timeout.

The prompt requests a department code from active database departments, category, `LOW|MEDIUM|HIGH` priority, and a short summary. JSON is parsed and the department/priority/category/summary are validated. Provider details are not returned to users. Missing credentials return 503; provider, timeout, and malformed output return a generic 502. There is no static classifier fallback: the user sees an unavailable/error response and ordinary grievance submission remains usable without AI.

Duplicate-grievance detection is not implemented; it was optional in the assessment brief. The current AI endpoint returns suggestions and summary only.

The endpoint returns `advisory: true` and a Django-signed recommendation token that expires after 30 minutes and binds the suggestions to a SHA-256 hash of the exact description. When submitted with the grievance, the token is verified and a separate `AIRecommendation` row is stored. It does not set official grievance values. The CMO queue displays the suggestion. A CMO must accept it or submit an explicit override; either action records reviewer and timestamp, updates official values, and creates internal history. The citizen never controls an official decision through AI fields.

The token is signed, not encrypted; it contains recommendation values and should not be logged. Provider data handling and retention must be assessed before real personal information is used. This fictional prototype must use fictional complaint text. No live credential or hosted provider call was available during local verification; provider behavior is covered with mocked success/failure tests.

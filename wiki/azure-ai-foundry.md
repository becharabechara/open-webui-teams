# Azure AI Foundry Support Modifications

This section details the modifications made to the OpenWebUI project to enable compatibility with Azure AI Foundry. The changes include adding API version configurations and updating backend endpoints to include appropriate headers.

## In `backend/open_webui/config.py`

A new configuration section was added at line 785, before the `OPENAI_API` section, to support Azure AI API versioning and OpenAI embeddings API versioning:

```python
####################################
# OPENAI_API_VERSION
####################################

AZURE_AI_API_VERSION = PersistentConfig(
    "AZURE_AI_API_VERSION",
    "azure_ai.api_version",
    os.environ.get("AZURE_AI_API_VERSION", "2024-05-01-preview"),
)

OPENAI_EMBEDDINGS_API_VERSION = PersistentConfig(
    "OPENAI_EMBEDDINGS_API_VERSION",
    "openai.embeddings_api_version",
    os.environ.get("OPENAI_EMBEDDINGS_API_VERSION", "2023-05-15"),
)
```

## In `backend/open_webui/routers/openai.py`

To integrate Azure AI API versioning, the following changes were made:

- Imported the `AZURE_AI_API_VERSION` configuration:

  ```python
  from open_webui.config import AZURE_AI_API_VERSION
  ```

- Added the `API-Version` header to the following endpoints:

  - `get_models`
  - `verify_connection`
  - `generate_chat_completion`
  - `proxy`

  The header was included as:

  ```python
  headers={"API-Version": AZURE_AI_API_VERSION}
  ```

## In `backend/open_webui/retrieval/utils.py`

To support embeddings with Azure AI, the following changes were made:

- Imported the `OPENAI_EMBEDDINGS_API_VERSION` configuration:

  ```python
  from open_webui.config import OPENAI_EMBEDDINGS_API_VERSION
  ```

- Modified the `generate_openai_batch_embeddings` function to include the API version in the request:

  ```python
  r = requests.post(
      f"{url}/embeddings?api-version={OPENAI_EMBEDDINGS_API_VERSION}",
      headers={
          "Content-Type": "application/json",
          "api-key": key,
          # "Authorization": f"Bearer {key}",
          **(
              {
                  "X-OpenWebUI-User-Name": user.name,
                  "X-OpenWebUI-User-Id": user.id,
                  "X-OpenWebUI-User-Email": user.email,
                  "X-OpenWebUI-User-Role": user.role,
              }
              if ENABLE_FORWARD_USER_INFO_HEADERS and user
              else {}
          ),
      },
      json={"input": texts, "model": model},
  )
  ```

These modifications ensure that the OpenWebUI backend correctly interacts with Azure AI Foundry's API endpoints using the appropriate versioning.
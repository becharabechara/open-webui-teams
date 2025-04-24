# Tikehau Capital Lagoon Branding Modifications

This section documents the modifications applied to the OpenWebUI project to align with Tikehau Capital Lagoon branding. The changes involve replacing static resources and updating configuration files to reflect the new branding identity.

## Static Resource Replacements

The following static resources were replaced to incorporate Tikehau Capital Lagoon branding:

### In `backend/open_webui/static/`

The following files were updated:

- `apple-touch-icon.png`
- `favicon-96x96.png`
- `favicon-dark.png`
- `favicon.ico`
- `favicon.png`
- `logo.png`
- `site.webmanifest` (updated `"name"` and `"short_name"` fields)
- `splash-dark.png`
- `splash.png`
- `web-app-manifest-192x192.png`
- `web-app-manifest-512x512.png`

### In `static/static/`

The same set of files was updated to maintain consistency:

- `apple-touch-icon.png`
- `favicon-96x96.png`
- `favicon-dark.png`
- `favicon.ico`
- `favicon.png`
- `logo.png`
- `site.webmanifest` (updated `"name"` and `"short_name"` fields)
- `splash-dark.png`
- `splash.png`
- `web-app-manifest-192x192.png`
- `web-app-manifest-512x512.png`

### In `static/`

- `favicon.png` was replaced.

## Configuration Changes

### In `backend/open_webui/env.py`

To prevent the default Open WebUI branding from being appended, the following lines were commented out:

- Line 110: `WEBUI_NAME = os.environ.get("WEBUI_NAME", "Open WebUI")`
- Line 111: `# if WEBUI_NAME != "Open WebUI":`
- Line 112: `#     WEBUI_NAME += " (Open WebUI)"`

This ensures that the `WEBUI_NAME` reflects the custom branding without additional text.

### In `backend/open_webui/utils/webhook.py`

To use a local favicon instead of the default `WEBUI_FAVICON_URL`, the following changes were made:

- Added a constant for the local favicon path:

  ```python
  LOCAL_FAVICON_PATH = "/static/favicon.ico"
  ```

- Modified the `payload` dictionary to use the local favicon path:

  ```python
  payload = {
      "@type": "MessageCard",
      "@context": "http://schema.org/extensions",
      "themeColor": "0076D7",
      "summary": message,
      "sections": [
          {
              "activityTitle": message,
              "activitySubtitle": f"{name} ({VERSION}) - {action}",
              # "activityImage": WEBUI_FAVICON_URL,
              "activityImage": LOCAL_FAVICON_PATH,
              "facts": facts,
              "markdown": True,
          }
      ],
  }
  ```

These changes ensure that webhook notifications display the Tikehau Capital Lagoon favicon.
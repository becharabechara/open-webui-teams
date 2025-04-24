# Environment Variables in OpenWebUI

This section documents the environment variables configured for the OpenWebUI project, explaining their purpose and usage. These variables control various aspects of the application, including security, authentication, API integrations, and vector database settings.

## Cross-Origin Resource Sharing (CORS) and Security Settings

- `CORS_ALLOW_ORIGIN="<private-domain>;<public-domain>;https://teams.microsoft.com"`  
  Defines the allowed origins for CORS requests, enabling cross-origin access from specified domains. In this case, it allows requests from a private domain, a public domain, and Microsoft Teams for integration purposes.

- `WEBUI_SESSION_COOKIE_SAME_SITE=None`  
  Controls the `SameSite` attribute for session cookies. Setting it to `None` allows cookies to be sent in cross-site requests, which is necessary for integrations like Microsoft Teams.

- `WEBUI_AUTH_COOKIE_SAME_SITE=None`  
  Similar to `WEBUI_SESSION_COOKIE_SAME_SITE`, this sets the `SameSite` attribute for authentication cookies to `None` to support cross-site authentication flows.

- `WEBUI_SESSION_COOKIE_SECURE=True`  
  Ensures that session cookies are only sent over HTTPS connections, enhancing security by preventing transmission over unencrypted HTTP.

- `WEBUI_AUTH_COOKIE_SECURE=True`  
  Ensures that authentication cookies are only sent over HTTPS, aligning with best practices for secure cookie handling.

- `ENABLE_TEAMS_XFRAME=True`  
  A custom variable that likely enables embedding OpenWebUI within an iframe for Microsoft Teams integration, bypassing default X-Frame-Options restrictions.

- `XFRAME_OPTIONS=""`  
  Sets the `X-Frame-Options` HTTP header to an empty string, allowing the application to be embedded in iframes (e.g., for Teams integration). This overrides any default restrictions on framing.

- `VITE_SHOW_TEAMS_AUTH_STEPS=True`  
  A custom variable likely used by the Vite frontend to display authentication steps specific to Microsoft Teams integration, guiding users through the login process.

## Authentication and OAuth Settings

- `WEBUI_AUTH=True`  
  Enables authentication for OpenWebUI, requiring users to log in to access the application.

- `ENABLE_OAUTH_LOGIN=True`  
  Enables OAuth-based login, allowing users to authenticate using an external identity provider (in this case, Microsoft Entra ID).

- `ENABLE_OAUTH_SIGNUP=True`  
  Allows new users to sign up via OAuth, creating accounts automatically during their first login with the OAuth provider.

- `ENABLE_LOGIN_FORM=False`  
  Disables the default login form, forcing users to authenticate via OAuth instead of a username/password form.

- `OAUTH_MERGE_ACCOUNTS_BY_EMAIL=True`  
  When enabled, this merges OAuth accounts with existing accounts based on email addresses, preventing duplicate accounts for the same user.

- `MICROSOFT_CLIENT_TENANT_ID=<entra-id-tenant>`  
  Specifies the Microsoft Entra ID tenant ID for OAuth authentication, identifying the organization’s Azure AD tenant.

- `MICROSOFT_CLIENT_ID=<entra-id-client-id>`  
  The client ID of the application registered in Microsoft Entra ID, used for OAuth authentication.

- `MICROSOFT_CLIENT_SECRET=<entra-id-secret>`  
  The client secret for the Entra ID application, used to authenticate the application with Microsoft’s OAuth service.

- `WEBUI_URL=<public-domain>`  
  Defines the public URL where OpenWebUI is hosted, used for generating callback URLs during OAuth flows and other external links.

- `WEBUI_NAME="Lagoon"`  
  Sets the name of the OpenWebUI instance to "Lagoon," reflecting the Tikehau Capital Lagoon branding.

- `MICROSOFT_OAUTH_SCOPE="openid email profile offline_access User.Read"`  
  Specifies the OAuth scopes requested during Microsoft Entra ID authentication. These scopes allow access to the user’s identity (`openid`), email (`email`), profile information (`profile`), refresh tokens (`offline_access`), and basic user data (`User.Read`).

## Lagoon API Integration

- `LAGOON_API_ENDPOINT="https://<api-archipel>/lagoon/api/chatv2/chatopenwebuistreaming"`  
  The endpoint for the Lagoon API used for streaming chat functionality in OpenWebUI, likely a custom integration for Tikehau Capital.

- `LAGOON_API_TASKENDPOINT="https://<api-archipel>/lagoon/api/chatv2/taskopenwebui"`  
  The endpoint for task-related API calls in the Lagoon integration, possibly for managing asynchronous tasks in OpenWebUI.

- `LAGOON_API_KEY=""`  
  The API key for authenticating with the Lagoon API. Currently empty, indicating no key is required (see `LAGOON_NEEDS_API_KEY`).

- `LAGOON_NEEDS_API_KEY="false"`  
  Indicates whether the Lagoon API requires an API key for authentication. Set to `false`, meaning authentication is not enforced.

- `LAGOON_SERVER_CERTIFICATE="false"`  
  Disables server certificate verification for the Lagoon API, likely for testing or development purposes. In production, this should be set to `true` for security.

## Vector Database Configuration

- `VECTOR_DB_PROVIDER="qdrant"`  
  Specifies Qdrant as the vector database provider for OpenWebUI, used for storing and querying embeddings (e.g., for search or RAG features).

- `QDRANT_URL="http://localhost:6333"`  
  The URL of the Qdrant server instance. Set to `localhost:6333`, indicating a local deployment of Qdrant.

- `QDRANT_API_KEY="<api-key>"`  
  The API key for authenticating with the Qdrant server. Replace `<api-key>` with the actual key if authentication is required.

## Tika Server Configuration

- `TIKA_SERVER_ENDPOINT="http://tika:9998"`  
  The endpoint for the Tika server, used for document parsing and text extraction in OpenWebUI (e.g., for processing PDFs or Word documents).

- `TIKA_VERSION="2.9.1.0"`  
  Specifies the version of the Tika server being used, ensuring compatibility with OpenWebUI.

- `TIKA_PORT="9998"`  
  The port on which the Tika server is running, matching the port in `TIKA_SERVER_ENDPOINT`.

- `TIKA_HEALTHCHECK_INTERVAL="30s"`  
  The interval at which health checks are performed on the Tika server, set to 30 seconds.

- `TIKA_HEALTHCHECK_TIMEOUT="10s"`  
  The timeout for Tika server health checks, set to 10 seconds.

- `TIKA_HEALTHCHECK_RETRIES="3"`  
  The number of retries for Tika server health checks before considering the server unhealthy, set to 3 attempts.

---

These environment variables configure OpenWebUI for secure operation, Microsoft Teams integration, OAuth authentication, and integration with external services like Lagoon, Qdrant, and Tika.
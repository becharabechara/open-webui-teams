# Teams Custom Integration

This section documents the custom Microsoft Teams integration for the OpenWebUI project, enabling seamless authentication and embedding within Teams. The integration leverages the Microsoft Teams SDK to handle authentication, bypasses the native OpenWebUI authentication flow for Teams contexts, and ensures compatibility across Teams desktop, mobile (iOS and Android), and embedded environments.

## Native OpenWebUI Authentication Flow

OpenWebUI's default authentication flow uses OAuth to authenticate users via an external identity provider, such as Microsoft Entra ID. Here's how it works:

1. **Redirect to `/auth`**: When a user attempts to access OpenWebUI without an active session (i.e., no valid `localStorage.token`), the application redirects them to the `/auth` route with a `redirect` query parameter specifying the original URL (e.g., `/auth?redirect=/`).

2. **OAuth Initiation**: The `/auth` route initiates an OAuth flow with the configured provider (Microsoft Entra ID in this case). The user is redirected to `login.microsoftonline.com`, Microsoft's OAuth authorization endpoint, where they authenticate using their Microsoft credentials.

3. **Authorization Code Grant**: After successful authentication, Microsoft redirects the user back to OpenWebUI's callback URL (e.g., `/oauth/microsoft/callback`) with an authorization code in the query parameters.

4. **Token Exchange**: The OpenWebUI backend (via `backend/open_webui/main.py`) exchanges the authorization code for an access token, refresh token, and ID token by making a request to Microsoft's token endpoint. This is done using the client ID (`MICROSOFT_CLIENT_ID`) and client secret (`MICROSOFT_CLIENT_SECRET`) configured in the environment variables.

5. **User Data Retrieval**: The backend uses the access token to fetch user information (e.g., email, name, profile picture) from Microsoft's userinfo endpoint (via Microsoft Graph API, scope `User.Read`).

6. **Session Creation**:
   - The backend creates or updates a user in the database (`Users` model) based on the OAuth subject ID (`sub`) and email.
   - A JWT token is generated using the user's ID (`create_token` function in `backend/open_webui/utils/auth.py`) and stored in `localStorage.token`.
   - The token is also set as a cookie (`oauth_id_token`) with attributes defined by `WEBUI_AUTH_COOKIE_SAME_SITE` and `WEBUI_AUTH_COOKIE_SECURE`.

7. **Session Storage**:
   - The user's information (ID, email, name, role) is stored in the Svelte store (`$user`) for client-side access.
   - The backend emits a `user-join` event via WebSocket (`$socket.emit('user-join', { auth: { token: sessionUser.token } })`) to notify the server of the user's session.

8. **Redirection**: After successful authentication, the user is redirected to the original URL specified in the `redirect` query parameter (e.g., `/`).

This flow ensures secure authentication but requires a browser redirect to Microsoft's login page, which can be disruptive in embedded contexts like Microsoft Teams.

## Microsoft Teams Authentication Flow

To provide a seamless experience within Microsoft Teams, OpenWebUI integrates with the Microsoft Teams SDK to perform Single Sign-On (SSO) using the Teams authentication token. Here's how the Teams authentication flow works:

1. **Teams Context Detection**:
   - The application detects if it's running within a Teams context (desktop, mobile, or embedded) using the `isTeamsContext` function (defined in `src/app.html` and reused in other files). This function checks the user agent for "teams" and inspects window properties for embedding indicators (`window.nativeInterface`, `window.name`).
   - For mobile detection, `isTeamsMobile` further checks for mobile-specific user agents and Teams app identifiers.

2. **Teams SDK Initialization**:
   - The Microsoft Teams SDK is loaded via a script tag in `src/app.html`:
     ```html
     <script src="https://res.cdn.office.net/teams-js/2.36.0/js/MicrosoftTeams.min.js" defer></script>
     ```
   - If a Teams context is detected, the SDK is initialized using `window.microsoftTeams.initialize()`. The `waitForTeamsSDK` function ensures the SDK is loaded before proceeding, with a timeout mechanism to handle failures.

3. **Client-Side Token Retrieval**:
   - The Teams SDK's `getAuthToken` method is called to obtain a client-side token:
     ```javascript
     window.microsoftTeams.authentication.getAuthToken({
         successCallback: async (token) => {
             addStepMessage($i18n.t('Auth token received'));
             if (await tryTeamsAuth(token)) {
                 loading = false;
             }
         },
         failureCallback: (error) => {
             addErrorMessage('N/A', $i18n.t(`Authentication failed: ${error}`), true);
             loading = false;
             document.getElementById('splash-screen')?.remove();
         }
     });
     ```
   - This token is a JSON Web Token (JWT) issued by Microsoft Teams, representing the user's identity within the Teams environment. It includes claims like the user's tenant ID and object ID but cannot be used directly for server-side API calls.

4. **Token Exchange (On-Behalf-Of Flow)**:
   - The client-side token is sent to the OpenWebUI backend via a POST request to `/api/teams/auth`:
     ```javascript
     const response = await fetch('/api/teams/auth', {
         method: 'POST',
         headers: {
             'Content-Type': 'application/json',
             'Accept': 'application/json'
         },
         body: JSON.stringify({ token })
     });
     ```
   - The backend (`backend/open_webui/main.py`) handles the request in the `teams_auth_api` endpoint. It uses the OAuth On-Behalf-Of flow to exchange the client-side token for a server-side access token:
     ```python
     token_data = await client.fetch_access_token(
         grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
         assertion=token,
         client_id=os.getenv("MICROSOFT_CLIENT_ID"),
         client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
         scope="openid profile email User.Read",
         requested_token_use="on_behalf_of"
     )
     ```
   - This exchange is performed with Microsoft Entra ID, using the client ID and secret to authenticate OpenWebUI as the application. The resulting access token can be used to call Microsoft Graph APIs on behalf of the user.

5. **User Data Retrieval**:
   - The backend uses the new access token to fetch user information from Microsoft's userinfo endpoint:
     ```python
     user_data = await client.userinfo(token=token_data)
     ```
   - The user data includes the email, name, and profile picture URL, which is fetched from Microsoft Graph if available.

6. **Session Creation**:
   - The `process_user_session` function creates or updates the user in the database, generates a JWT token, and sets it as a cookie (`oauth_id_token`).
   - The client receives the user data and token, stores the token in `localStorage.token`, updates the Svelte store (`$user`), and emits a `user-join` event via WebSocket, mirroring the native flow.

7. **Redirection**:
   - After successful authentication, the user is redirected to the intended page (e.g., `/`) without leaving the Teams environment.

This flow avoids browser redirects, providing a native app-like experience within Teams.

## Bypassing Native `/auth` Redirection for Teams Contexts

To prevent the disruptive redirect to `/auth` in Teams contexts, OpenWebUI was modified to detect Teams environments and bypass the default authentication flow:

1. **Teams Context Detection**:
   - The `isTeamsContext` function (added in `src/app.html`, `src/routes/teams`, and `src/routes/+layout.svelte`) identifies Teams contexts by checking:
     - User agent for "teams" (desktop and mobile).
     - Window properties for embedding (`window.nativeInterface`, `window.name` values like `embedded-page-container` or `extension-tab-frame`).
     - Mobile-specific identifiers for Teams apps (`com.microsoft.skype.teams`, `teamsmobile`).

2. **Skipping `/auth` Redirect**:
   - In `src/routes/+layout.svelte`, the authentication logic was modified to skip the redirect to `/auth` when in a Teams context and on the `/teams` route:
     ```javascript
     if (localStorage.token) {
         const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
             toast.error(`${error}`);
             return null;
         });

         if (sessionUser) {
             $socket.emit('user-join', { auth: { token: sessionUser.token } });
             await user.set(sessionUser);
             await config.set(await getBackendConfig());
         } else {
             if (isTeamsContext() && $page.url.pathname === '/teams') {
                 console.log('Skipping /auth redirect in Teams context on /teams');
             } else {
                 localStorage.removeItem('token');
                 await goto(`/auth?redirect=${encodedUrl}`);
             }
         }
     } else {
         if (isTeamsContext() && $page.url.pathname === '/teams') {
             console.log('Skipping /auth redirect in Teams context on /teams');
         } else if ($page.url.pathname !== '/auth') {
             await goto(`/auth?redirect=${encodedUrl}`);
         }
     }
     ```
   - This ensures that users in Teams are not redirected to `/auth`, which would break the embedded experience.

3. **Root Path Redirection**:
   - In `backend/open_webui/main.py`, a `TeamsRedirectMiddleware` was added to redirect root path requests (`/`) to `/teams` if a Teams context is detected:
     ```python
     class TeamsRedirectMiddleware(BaseHTTPMiddleware):
         async def dispatch(self, request: Request, call_next):
             if request.method == "GET" and request.url.path == "/":
                 user_agent = request.headers.get("User-Agent", "").lower()
                 is_teams = "teams" in user_agent
                 if is_teams:
                     return RedirectResponse(url="/teams")
             response = await call_next(request)
             return response
     ```
   - This middleware ensures that Teams users are directed to the `/teams` route, where the Teams-specific authentication flow is handled.

4. **Security Headers Adjustment**:
   - In `backend/open_webui/utils/security_headers.py`, the `ENABLE_TEAMS_XFRAME` environment variable (`True` in your setup) enables embedding in Teams by setting a `Content-Security-Policy` header with `frame-ancestors`:
     ```python
     def set_content_security_policy_teams():
         value = "frame-ancestors 'self' https://teams.microsoft.com"
         return {"Content-Security-Policy": value}
     ```
   - This overrides the default `X-Frame-Options: DENY` header, allowing OpenWebUI to be embedded in an iframe from `https://teams.microsoft.com`.

This approach ensures that Teams users experience a seamless authentication flow without leaving the Teams environment, while non-Teams users follow the native `/auth` flow.

## Modified Files

Below are the code changes made to implement the Teams integration.

### `package.json`

Added the Microsoft Teams SDK dependency:

```json
"@microsoft/teams-js": "^2.36.0",
```

### `src/app.html`

Added the Teams SDK script and initialization logic:

```html
</script>
<!-- Add Microsoft Teams SDK -->
<script src="https://res.cdn.office.net/teams-js/2.36.0/js/MicrosoftTeams.min.js" defer></script>
<script>
    // Reuse the same Teams detection logic as in src/routes/teams/+page.svelte
    function isTeamsContext() {
        const userAgent = navigator.userAgent.toLowerCase();
        const isTeams = userAgent.includes("teams");
        const isEmbedded = 
            (window.parent === window.self && window.nativeInterface) ||
            window.name === "embedded-page-container" ||
            window.name === "extension-tab-frame";
        return isTeams || isEmbedded;
    }

    // Wait for the Teams SDK to load
    function waitForTeamsSDK(callback, timeout = 5000) {
        const startTime = Date.now();
        function checkSDK() {
            if (typeof window.microsoftTeams !== 'undefined') {
                callback();
            } else if (Date.now() - startTime < timeout) {
                setTimeout(checkSDK, 100);
            } else {
                // If SDK fails to load within timeout, proceed without initialization
                console.log('Teams SDK failed to load within timeout');
            }
        }
        checkSDK();
    }

    // Initialize Teams SDK if in Teams context
    if (isTeamsContext()) {
        waitForTeamsSDK(() => {
            if (typeof window.microsoftTeams !== 'undefined') {
                window.microsoftTeams.initialize(() => {
                    window.microsoftTeams.appInitialization.notifyAppLoaded();
                    window.microsoftTeams.appInitialization.notifySuccess();
                });
            }
        });
    }
</script>
```

### `src/routes/teams/+page.svelte`

Created a new route to handle Teams authentication:

```html
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { getContext } from 'svelte';
    import { user, socket } from '$lib/stores';
    import { page } from '$app/stores';
    import { toast } from 'svelte-sonner';
    import { getSessionUser } from '$lib/apis/auths';

    const i18n = getContext('i18n');
    const showSteps = import.meta.env.VITE_SHOW_TEAMS_AUTH_STEPS === 'true';
    let loading = true;
    let errorMessages = [];
    let stepMessages = [];
    let teamsContext = false;
    let teamsMobile = false;

    const isTeamsContext = () => {
        const userAgent = navigator.userAgent.toLowerCase();
        const isTeams = userAgent.includesanha("teams");
        const isEmbedded = 
            (window.parent === window.self && window.nativeInterface) ||
            window.name === "embedded-page-container" ||
            window.name === "extension-tab-frame" ||
            userAgent.includes("electron");
        return isTeams || isEmbedded;
    };

    const isTeamsMobile = () => {
        const userAgent = navigator.userAgent.toLowerCase();
        const isTeams = userAgent.includes("teams");
        const isMobile = /mobile|android|iphone|ipad|ipod/.test(userAgent);
        const isTeamsMobileApp = userAgent.includes("com.microsoft.skype.teams") || userAgent.includes("teamsmobile");
        return isTeams && isMobile && isTeamsMobileApp;
    };

    const addStepMessage = (message) => {
        if (showSteps || errorMessages.length > 0) {
            stepMessages = [...stepMessages, { message, timestamp: new Date().toISOString() }];
        }
    };

    const addErrorMessage = (status, message, significant = false) => {
        errorMessages = [...errorMessages, { status, message, timestamp: new Date().toISOString() }];
        if (significant) {
            toast.error(message);
        }
    };

    const setSessionUser = async (sessionUser) => {
        addStepMessage($i18n.t('Setting session user'));
        if (sessionUser && sessionUser.token) {
            localStorage.token = sessionUser.token;
            await user.set(sessionUser);
            $socket.emit('user-join', { auth: { token: sessionUser.token } });
            if (teamsContext && typeof window.microsoftTeams !== 'undefined') {
                window.microsoftTeams.appInitialization.notifySuccess();
            }
            toast.success($i18n.t('Connection successful!'));
            // Clear messages on success
            errorMessages = [];
            stepMessages = [];
            setTimeout(() => {
                const redirectUrl = new URLSearchParams(window.location.search).get('redirect') || '/';
                if (typeof redirectUrl !== 'string' || !redirectUrl.startsWith('/')) {
                    addErrorMessage('N/A', $i18n.t('Invalid redirect URL'), true);
                    goto('/');
                    return;
                }
                loading = false;
                document.getElementById('splash-screen')?.remove();
                addStepMessage($i18n.t('Redirecting to: ' + redirectUrl));
                goto(redirectUrl);
            }, 2000);
        } else {
            addErrorMessage('N/A', $i18n.t('Invalid session user data'), true);
            loading = false;
        }
    };

    const waitForTeamsSDK = (callback, timeout = 20000) => {
        addStepMessage($i18n.t('Waiting for Teams SDK'));
        const startTime = Date.now();
        function checkSDK() {
            if (typeof window.microsoftTeams !== 'undefined') {
                addStepMessage($i18n.t('Teams SDK loaded'));
                callback();
            } else if (Date.now() - startTime < timeout) {
                setTimeout(checkSDK, 100);
            } else {
                addErrorMessage('N/A', $i18n.t('Failed to initialize Teams SDK'), true);
                loading = false;
                document.getElementById('splash-screen')?.remove();
            }
        }
        const sdkScript = document.querySelector('script[src*="MicrosoftTeams.min.js"]');
        if (!sdkScript) {
            addErrorMessage('N/A', $i18n.t('Teams SDK script not found'), true);
            loading = false;
            document.getElementById('splash-screen')?.remove();
            return;
        }
        checkSDK();
    };

    const tryTeamsAuth = async (token, retryCount = 0, maxRetries = 3) => {
        addStepMessage($i18n.t(`Attempting Teams auth, retry ${retryCount + 1}/${maxRetries}`));
        try {
            const response = await fetch('/api/teams/auth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ token })
            });
            const contentType = response.headers.get('content-type') || 'unknown';
            const status = response.status;

            if (status === 502 && retryCount < maxRetries) {
                addErrorMessage(status, $i18n.t(`HTTP 502: Retrying (${retryCount + 1}/${maxRetries})`));
                await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                return await tryTeamsAuth(token, retryCount + 1, maxRetries);
            }

            if (!response.ok) {
                if (contentType.includes('application/json')) {
                    const errorData = await response.json();
                    throw new Error($i18n.t(`HTTP ${status}: ${errorData.detail || 'Unknown error'}`));
                } else {
                    const rawText = await response.text();
                    throw new Error($i18n.t(`HTTP ${status}, Content-Type: ${contentType}, Response: "${rawText}"`));
                }
            }

            if (!contentType.includes('application/json')) {
                const rawText = await response.text();
                throw new Error($i18n.t(`Expected JSON but received: ${rawText}`));
            }

            const sessionUser = await response.json();
            if (sessionUser && sessionUser.token) {
                await setSessionUser(sessionUser);
                return true;
            }
            throw new Error($i18n.t('Invalid response: missing user data'));
        } catch (error) {
            addErrorMessage('N/A', error.message, retryCount >= maxRetries);
            loading = false;
            document.getElementById('splash-screen')?.remove();
            return false;
        }
    };

    const checkOauthCallback = async () => {
        addStepMessage($i18n.t('Checking OAuth callback'));
        if (!$page.url.hash) return;
        const params = new URLSearchParams($page.url.hash.substring(1));
        const token = params.get('token');
        if (!token) return;
        const sessionUser = await getSessionUser(token).catch((error) => {
            addErrorMessage('N/A', $i18n.t(`Failed to fetch user: ${error}`), true);
            return null;
        });
        if (sessionUser) {
            await setSessionUser(sessionUser);
        }
    };

    onMount(async () => {
        addStepMessage($i18n.t('Initializing Teams context'));
        teamsContext = isTeamsContext();
        teamsMobile = isTeamsMobile();
        document.getElementById('splash-screen')?.remove();

        if ($user) {
            const redirectUrl = new URLSearchParams(window.location.search).get('redirect') || '/';
            if (typeof redirectUrl !== 'string' || !redirectUrl.startsWith('/')) {
                addErrorMessage('N/A', $i18n.t('Invalid redirect URL'), true);
                goto('/');
                return;
            }
            loading = false;
            addStepMessage($i18n.t('Redirecting to: ' + redirectUrl));
            goto(redirectUrl);
            return;
        }

        if (!teamsContext) {
            loading = false;
            return;
        }

        await checkOauthCallback();

        waitForTeamsSDK(() => {
            try {
                addStepMessage($i18n.t('Initializing Teams SDK'));
                window.microsoftTeams.initialize();
                addStepMessage($i18n.t('Notifying app loaded'));
                window.microsoftTeams.appInitialization.notifyAppLoaded();

                addStepMessage($i18n.t('Requesting auth token'));
                window.microsoftTeams.authentication.getAuthToken({
                    successCallback: async (token) => {
                        addStepMessage($i18n.t('Auth token received'));
                        if (await tryTeamsAuth(token)) {
                            loading = false;
                        }
                    },
                    failureCallback: (error) => {
                        addErrorMessage('N/A', $i18n.t(`Authentication failed: ${error}`), true);
                        loading = false;
                        document.getElementById('splash-screen')?.remove();
                    }
                });
            } catch (error) {
                addErrorMessage('N/A', $i18n.t(`Teams SDK initialization error: ${error.message}`), true);
                loading = false;
                document.getElementById('splash-screen')?.remove();
            }
        });
    });
</script>

<div class="w-full h-screen flex flex-col items-center justify-center p-4 space-y-4">
    {#if loading}
        <div class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Authenticating...')}</div>
    {/if}

    {#if errorMessages.length > 0}
        <div class="w-full bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded">
            <h2 class="text-lg font-semibold mb-2">{$i18n.t('Errors')}</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full text-sm text-left">
                    <thead class="text-xs uppercase bg-red-200 dark:bg-red-800">
                        <tr>
                            <th scope="col" class="px-4 py-2 whitespace-nowrap">{$i18n.t('Timestamp')}</th>
                            <th scope="col" class="px-4 py-2 whitespace-nowrap">{$i18n.t('Status')}</th>
                            <th scope="col" class="px-4 py-2">{$i18n.t('Message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each errorMessages as error}
                            <tr class="border-b dark:border-red-700">
                                <td class="px-4 py-2 whitespace-nowrap">{new Date(error.timestamp).toLocaleString()}</td>
                                <td class="px-4 py-2 whitespace-nowrap">{error.status}</td>
                                <td class="px-4 py-2 break-words">{error.message}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}

    {#if (showSteps || errorMessages.length > 0) && stepMessages.length > 0}
        <div class="w-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 p-4 rounded">
            <h2 class="text-lg font-semibold mb-2">{$i18n.t('Steps')}</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full text-sm text-left">
                    <thead class="text-xs uppercase bg-blue-200 dark:bg-blue-800">
                        <tr>
                            <th scope="col" class="px-4 py-2 whitespace-nowrap">{$i18n.t('Timestamp')}</th>
                            <th scope="col" class="px-4 py-2">{$i18n.t('Message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each stepMessages as step}
                            <tr class="border-b dark:border-blue-700">
                                <td class="px-4 py-2 whitespace-nowrap">{new Date(step.timestamp).toLocaleString()}</td>
                                <td class="px-4 py-2 break-words">{step.message}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>

<style>
    .min-w-full { width: 100%; }
    .overflow-x-auto { overflow-x: auto; }
    table { border-collapse: collapse; }
    th, td { text-align: left; }
    .break-words { word-break: break-word; }
    @media (max-width: 640px) {
        .text-lg { font-size: 1.125rem; }
        th, td { font-size: 0.75rem; padding: 0.5rem; }
    }
</style>
```

### `src/routes/+layout.svelte`

Added Teams context detection and modified authentication logic:

```javascript
const isTeamsContext = () => {
    const userAgent = navigator.userAgent.toLowerCase();
    const isTeams = userAgent.includes("teams");
    const isEmbedded = 
        (window.parent === window.self && window.nativeInterface) ||
        window.name === "embedded-page-container" ||
        window.name === "extension-tab-frame";
    return isTeams || isEmbedded;
};

// In the onMount function, within the if(backendConfig) { ... if($config) ... block:
if (localStorage.token) {
    // Get Session User Info
    const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
        toast.error(`${error}`);
        return null;
    });

    if (sessionUser) {
        // Save Session User to Store
        $socket.emit('user-join', { auth: { token: sessionUser.token } });

        await user.set(sessionUser);
        await config.set(await getBackendConfig());
    } else {
        // Skip redirect to /auth for Teams context on /teams
        if (isTeamsContext() && $page.url.pathname === '/teams') {
            console.log('Skipping /auth redirect in Teams context on /teams');
        } else {
            localStorage.removeItem('token');
            await goto(`/auth?redirect=${encodedUrl}`);
        }
    }
} else {
    // Skip redirect to /auth for Teams context on /teams
    if (isTeamsContext() && $page.url.pathname === '/teams') {
        console.log('Skipping /auth redirect in Teams context on /teams');
    } else if ($page.url.pathname !== '/auth') {
        await goto(`/auth?redirect=${encodedUrl}`);
    }
}

// In the return statement:
return () => {
    window.removeEventListener('resize', onResize);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
};
```

### `backend/open_webui/utils/security_headers.py`

Modified to support Teams embedding:

```python
def set_security_headers() -> Dict[str, str]:
    """
    Sets security headers based on environment variables.

    This function reads specific environment variables and uses their values
    to set corresponding security headers. The headers that can be set are:
    - cache-control
    - permissions-policy
    - strict-transport-security
    - referrer-policy
    - x-content-type-options
    - x-download-options
    - x-frame-options
    - x-permitted-cross-domain-policies
    - content-security-policy

    Each environment variable is associated with a specific setter function
    that constructs the header. If the environment variable is set, the
    corresponding header is added to the options dictionary.

    ENABLE_TEAMS_XFRAME takes precedence over XFRAME_OPTIONS and uses Content-Security-Policy frame-ancestors.

    Returns:
        dict: A dictionary containing the security headers and their values.
    """
    options = {}
    header_setters = {
        "CACHE_CONTROL": set_cache_control,
        "HSTS": set_hsts,
        "PERMISSIONS_POLICY": set_permissions_policy,
        "REFERRER_POLICY": set_referrer,
        "XCONTENT_TYPE": set_xcontent_type,
        "XDOWNLOAD_OPTIONS": set_xdownload_options,
        "XFRAME_OPTIONS": set_xframe,
        "XPERMITTED_CROSS_DOMAIN_POLICIES": set_xpermitted_cross_domain_policies,
        "CONTENT_SECURITY_POLICY": set_content_security_policy,
    }

    # Process all headers except XFRAME_OPTIONS
    for env_var, setter in header_setters.items():
        if env_var != "XFRAME_OPTIONS":  # Skip XFRAME_OPTIONS initially
            value = os.environ.get(env_var)
            if value is not None:
                header = setter(value)
                if header:
                    options.update(header)

    # Handle ENABLE_TEAMS_XFRAME with CSP taking precedence
    enable_teams_xframe = os.environ.get("ENABLE_TEAMS_XFRAME", "False").lower() == "true"
    if enable_teams_xframe:
        header = set_content_security_policy_teams()
        options.update(header)
    else:
        xframe_value = os.environ.get("XFRAME_OPTIONS")
        if xframe_value is not None:
            header = set_xframe(xframe_value)
            if header:
                options.update(header)
        if "X-Frame-Options" not in options and "Content-Security-Policy" not in options:
            options["X-Frame-Options"] = "DENY"

    return options

# Set X-Frame-Options response header
def set_xframe(value: str):
    if value == "":
        return {}  # Empty string means no header
    pattern = r"^(DENY|SAMEORIGIN)$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "DENY"
    return {"X-Frame-Options": value}

# Set Content-Security-Policy for Teams-specific frame-ancestors
def set_content_security_policy_teams():
    """
    Sets the Content-Security-Policy header specifically for Microsoft Teams integration,
    allowing framing only from 'self' and 'https://teams.microsoft.com'.
    """
    value = "frame-ancestors 'self' https://teams.microsoft.com"
    return {"Content-Security-Policy": value}
```

### `backend/open_webui/main.py`

Added redirection middleware and Teams SSO endpoint:

```python
# Redirection Middleware (around line 862)
class TeamsRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request is a GET request to the root path
        if request.method == "GET" and request.url.path == "/":
            # Check for Teams in the User-Agent
            user_agent = request.headers.get("User-Agent", "").lower()
            is_teams = "teams" in user_agent
            # Redirect to /teams if in Teams context
            if is_teams:
                return RedirectResponse(url="/teams")
        
        # Proceed with the normal flow for other requests
        response = await call_next(request)
        return response

# Add the middlewares to the app
app.add_middleware(TeamsRedirectMiddleware)
app.add_middleware(RedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Microsoft Teams SSO Section (before the last function check and application mount)
##########################################################################
# Microsoft Teams SSO Applicationn Integration
##########################################################################

from open_webui.utils.oauth import auth_manager_config
from open_webui.utils.misc import parse_duration
from open_webui.utils.auth import create_token
from open_webui.env import WEBUI_AUTH_COOKIE_SAME_SITE, WEBUI_AUTH_COOKIE_SECURE
import httpx
import jwt
import uuid
import logging
import base64
import mimetypes
import aiohttp
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

async def process_user_session(oauth_manager: OAuthManager, request: Request, user_data: dict, access_token: str, id_token: str):
    """Process user data, fetch profile image, and generate a JWT token."""
    log.info("Processing user session")
    sub = user_data.get("sub")
    if not sub:
        log.error("Missing subject ID in user_data")
        raise HTTPException(400, detail="Invalid credentials: Missing subject ID")
    provider_sub = f"microsoft@{sub}"
    email = user_data.get(auth_manager_config.OAUTH_EMAIL_CLAIM, "").lower()
    if not email:
        log.error("Missing email in user_data")
        raise HTTPException(400, detail="Invalid credentials: Missing email")

    # Fetch and encode profile image
    picture_url = user_data.get(auth_manager_config.OAUTH_PICTURE_CLAIM, "/user.png")
    if picture_url and picture_url.startswith("https://graph.microsoft.com"):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {access_token}"}
                log.info(f"Fetching profile image for user {email}")
                async with session.get(picture_url, headers=headers) as resp:
                    if resp.ok:
                        picture = await resp.read()
                        base64_encoded_picture = base64.b64encode(picture).decode("utf-8")
                        guessed_mime_type = mimetypes.guess_type(picture_url)[0] or "image/jpeg"
                        picture_url = f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                        log.info(f"Profile image fetched for user {email}")
                    else:
                        error_text = await resp.text()
                        log.warning(f"No profile image found for user {email}: {resp.status} {error_text}")
                        picture_url = "/user.png"
        except Exception as e:
            log.error(f"Error fetching profile image for user {email}: {str(e)}")
            picture_url = "/user.png"

    user = Users.get_user_by_oauth_sub(provider_sub)
    if not user and auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL:
        user = Users.get_user_by_email(email)
        if user:
            log.info(f"Merging account for email {email} with oauth_sub {provider_sub}")
            Users.update_user_oauth_sub_by_id(user.id, provider_sub)

    role = oauth_manager.get_user_role(user, user_data)

    if not user:
        if not auth_manager_config.ENABLE_OAUTH_SIGNUP:
            log.error("Account creation disabled")
            raise HTTPException(403, detail="Account creation disabled")
        name = user_data.get(auth_manager_config.OAUTH_USERNAME_CLAIM, email.split("@")[0])
        log.info(f"Creating new user: email={email}, name={name}")
        user = Users.insert_new_user(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            profile_image_url=picture_url,
            role=role,
            oauth_sub=provider_sub,
        )
    else:
        if user.role != role:
            log.info(f"Updating user role from {user.role} to {role}")
            Users.update_user_role_by_id(user.id, role)
        Users.update_user_by_id(user.id, {
            "last_active_at": int(time.time()),
            "profile_image_url": picture_url
        })

    # Update user groups if enabled
    if auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT and role != "admin":
        log.info("Updating user groups")
        oauth_manager.update_user_groups(
            user=user,
            user_data=user_data,
            default_permissions=request.app.state.config.USER_PERMISSIONS or {}
        )

    token = create_token(
        data={"id": user.id},
        expires_delta=parse_duration(auth_manager_config.JWT_EXPIRES_IN)
    )
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": role,
        "token": token
    }

async def handle_teams_auth(request: Request, token: str, redirect_uri: Optional[str] = None):
    """Handle Teams authentication by validating the token and retrieving user info."""
    log.info("Handling Teams authentication")
    if not token:
        log.error("No token provided")
        raise HTTPException(400, detail="No token provided")

    try:
        client = oauth_manager.get_client("microsoft")
        if not client:
            log.error("Microsoft OAuth provider not configured")
            raise HTTPException(400, detail="Microsoft OAuth provider not configured")

        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                token_data = await client.fetch_access_token(
                    grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
                    assertion=token,
                    client_id=os.getenv("MICROSOFT_CLIENT_ID"),
                    client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
                    scope="openid profile email User.Read",
                    requested_token_use="on_behalf_of"
                )
                log.info("Token exchange successful")
                break
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                log.error(f"Token exchange attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries:
                    raise HTTPException(503, detail="Token exchange failed")
                await asyncio.sleep(1)

        if not token_data.get("access_token") or not token_data.get("id_token"):
            log.error("Invalid token response from provider")
            raise HTTPException(400, detail="Invalid token response from provider")

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                user_data = await client.userinfo(token=token_data)
                if not isinstance(user_data, dict):
                    log.error("Invalid userinfo response")
                    raise HTTPException(400, detail="Invalid userinfo response")
                log.info(f"User data retrieved for email {user_data.get('email', 'unknown')}")
                user_response = await process_user_session(oauth_manager, request, user_data, token_data.get("access_token"), token_data.get("id_token"))
                return {
                    "user": user_response,
                    "id_token": token_data.get("id_token")
                }
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                log.error(f"Userinfo attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries:
                    raise HTTPException(400, detail="Failed to fetch user info")
                await asyncio.sleep(1)

    except HTTPException as e:
        log.error(f"Authentication failed: {str(e)}")
        raise e
    except Exception as e:
        log.error(f"Unexpected error during authentication: {str(e)}")
        raise HTTPException(400, detail="Authentication failed")

class TeamsAuthRequest(BaseModel):
    token: str

@app.post("/api/teams/auth")
async def teams_auth_api(request: Request, body: TeamsAuthRequest):
    log.info("Received Teams auth request")
    try:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/oauth/microsoft/callback"
        result = await handle_teams_auth(request, body.token, redirect_uri)
        user = result["user"]
        id_token = result["id_token"]

        response = JSONResponse(content=user)
        response.set_cookie(
            key="oauth_id_token",
            value=id_token,
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )
        return response

    except Exception as e:
        log.error(f"Error in teams_auth_api: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

This integration enables OpenWebUI to function seamlessly within Microsoft Teams, providing a native authentication experience and ensuring compatibility across different Teams environments.
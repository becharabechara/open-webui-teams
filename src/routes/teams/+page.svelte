<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { user, socket } from '$lib/stores';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getSessionUser } from '$lib/apis/auths';

	const i18n = getContext('i18n');
	let loading = true;
	let errorMessages = [];
	let stepMessages = [];
	let successMessage = '';
	let teamsContext = false;
	let teamsMobile = false;

	const isTeamsContext = () => {
		const userAgent = navigator.userAgent.toLowerCase();
		const isTeams = userAgent.includes("teams");
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
		stepMessages = [...stepMessages, { message, timestamp: new Date().toISOString() }];
	};

	const setSessionUser = async (sessionUser) => {
		addStepMessage($i18n.t('Setting session user'));
		if (sessionUser) {
			if (sessionUser.token) localStorage.token = sessionUser.token;
			await user.set(sessionUser);
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			if (teamsContext && typeof window.microsoftTeams !== 'undefined') {
				window.microsoftTeams.appInitialization.notifySuccess();
			}
			toast.success($i18n.t('Connection successful!'));
			setTimeout(() => {
				const redirectUrl = new URLSearchParams(window.location.search).get('redirect') || '/';
				if (typeof redirectUrl !== 'string' || !redirectUrl.startsWith('/')) {
					const error = $i18n.t('Invalid redirect URL');
					errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
					toast.error(error);
					goto('/');
					return;
				}
				// Clear messages on success
				errorMessages = [];
				stepMessages = [];
				loading = false;
				// Remove splash screen before redirect
				document.getElementById('splash-screen')?.remove();
				addStepMessage($i18n.t('Redirecting to: ' + redirectUrl));
				goto(redirectUrl);
			}, 2000);
		} else {
			const error = $i18n.t('Invalid session user data');
			errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
			toast.error(error);
			loading = false;
		}
	};

	const waitForTeamsSDK = (callback, timeout = 20000) => {
		addStepMessage($i18n.t('Waiting for Teams SDK'));
		const startTime = Date.now();
		function checkSDK() {
			if (typeof window.microsoftTeams !== 'undefined') {
				addStepMessage($i18n.t('Teams SDK loaded successfully'));
				callback();
			} else if (Date.now() - startTime < timeout) {
				setTimeout(checkSDK, 100);
			} else {
				const error = $i18n.t('Failed to initialize Teams SDK');
				errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
				toast.error(error);
				loading = false;
				// Remove splash screen on error
				document.getElementById('splash-screen')?.remove();
			}
		}
		const sdkScript = document.querySelector('script[src*="MicrosoftTeams.min.js"]');
		if (!sdkScript) {
			const error = $i18n.t('Teams SDK script not found');
			errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
			toast.error(error);
			loading = false;
			// Remove splash screen on error
			document.getElementById('splash-screen')?.remove();
			return;
		}
		checkSDK();
	};

	const tryTeamsAuth = async (token, retryCount = 0, maxRetries = 3) => {
		addStepMessage($i18n.t(`Attempting Teams auth, retry ${retryCount + 1}/${maxRetries}`));
		try {
			const headers = {
				'Content-Type': 'application/json',
				'Accept': 'application/json'
			};
			const body = JSON.stringify({ token });
			const headerSize = Object.entries(headers).reduce((sum, [key, value]) => sum + key.length + value.length, 0);
			const totalRequestSize = headerSize + body.length;
			addStepMessage($i18n.t(`Auth request headers size: ${headerSize} bytes, Total request size: ${totalRequestSize} bytes`));
			const response = await fetch('/api/teams/auth', {
				method: 'POST',
				headers: headers,
				body: body
			});
			const contentType = response.headers.get('content-type') || 'unknown';
			const status = response.status;
			const responseHeaders = {};
			response.headers.forEach((value, key) => { responseHeaders[key] = value; });
			const responseHeaderSize = Object.entries(responseHeaders).reduce((sum, [key, value]) => sum + key.length + value.length, 0);
			addStepMessage($i18n.t(`Auth response headers size: ${responseHeaderSize} bytes`));

			if (status === 502 && retryCount < maxRetries) {
				const error = $i18n.t(`HTTP 502: Retrying (${retryCount + 1}/${maxRetries})`);
				errorMessages = [...errorMessages, { status, message: error, timestamp: new Date().toISOString() }];
				await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
				return await tryTeamsAuth(token, retryCount + 1, maxRetries);
			}

			if (!response.ok) {
				if (contentType.includes('application/json')) {
					const errorData = await response.json();
					const error = $i18n.t(`HTTP ${status}: ${errorData.detail || 'Unknown error'}`);
					errorMessages = [...errorMessages, { status, message: error, timestamp: new Date().toISOString() }];
					throw new Error(error);
				} else {
					const rawText = await response.text();
					const errorDetails = $i18n.t(`HTTP ${status}, Content-Type: ${contentType}, Response: "${rawText}"`);
					errorMessages = [...errorMessages, { status, message: errorDetails, timestamp: new Date().toISOString() }];
					throw new Error(errorDetails);
				}
			}

			if (response.redirected) {
				const url = new URL(response.url);
				const token = url.hash.match(/token=([^&]+)/)?.[1];
				if (token) {
					const sessionUser = await getSessionUser(token).catch((error) => {
						const errMsg = $i18n.t(`Failed to fetch user: ${error}`);
						errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
						throw new Error(errMsg);
					});
					await setSessionUser(sessionUser);
					return true;
				}
				const error = $i18n.t('Invalid redirect: missing token');
				errorMessages = [...errorMessages, { status, message: error, timestamp: new Date().toISOString() }];
				throw new Error(error);
			}

			if (!contentType.includes('application/json')) {
				const rawText = await response.text();
				const errorDetails = $i18n.t(`HTTP ${status}, Content-Type: ${contentType}, Response: "${rawText}"`);
				errorMessages = [...errorMessages, { status, message: errorDetails, timestamp: new Date().toISOString() }];
				throw new Error($i18n.t(`Expected JSON but received invalid response: ${errorDetails}`));
			}

			const sessionUser = await response.json();
			if (sessionUser && sessionUser.token) {
				await setSessionUser(sessionUser);
				return true;
			}
			const error = $i18n.t('Invalid response: missing user data');
			errorMessages = [...errorMessages, { status, message: error, timestamp: new Date().toISOString() }];
			throw new Error(error);
		} catch (error) {
			loading = false;
			toast.error(error.message);
			// Remove splash screen on error
			document.getElementById('splash-screen')?.remove();
			return false;
		}
	};

	const checkOauthCallback = async () => {
		addStepMessage($i18n.t('Checking OAuth callback'));
		if (!$page.url.hash) return;
		const hash = $page.url.hash.substring(1);
		if (!hash) return;
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) return;
		const sessionUser = await getSessionUser(token).catch((error) => {
			const errMsg = $i18n.t(`Failed to fetch user: ${error}`);
			errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
			toast.error(errMsg);
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

		// Remove splash screen initially
		document.getElementById('splash-screen')?.remove();

		// If user is authenticated, redirect to the specified URL or /
		if ($user) {
			addStepMessage($i18n.t('User already authenticated'));
			const redirectUrl = new URLSearchParams(window.location.search).get('redirect') || '/';
			if (typeof redirectUrl !== 'string' || !redirectUrl.startsWith('/')) {
				const error = $i18n.t('Invalid redirect URL');
				errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
				toast.error(error);
				goto('/');
				return;
			}
			// Clear messages on success
			errorMessages = [];
			stepMessages = [];
			loading = false;
			addStepMessage($i18n.t('Redirecting to: ' + redirectUrl));
			goto(redirectUrl);
			return;
		}

		// For non-Teams context, rely on +layout.svelte to handle redirect
		if (!teamsContext) {
			addStepMessage($i18n.t('Non-Teams context, exiting'));
			loading = false;
			return;
		}

		// Proceed with Teams authentication
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
						const errMsg = $i18n.t(`Authentication failed: ${error}`);
						errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
						toast.error(errMsg);
						loading = false;
						// Remove splash screen on error
						document.getElementById('splash-screen')?.remove();
					}
				});
			} catch (error) {
				const errMsg = $i18n.t(`Teams SDK initialization error: ${error.message}`);
				errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
				toast.error(errMsg);
				loading = false;
				// Remove splash screen on error
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

	{#if stepMessages.length > 0}
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

	{#if successMessage}
		<div class="w-full bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 p-4 rounded">
			<h2 class="text-lg font-semibold mb-2">{$i18n.t('Success')}</h2>
			<p class="text-sm">{$i18n.t(successMessage)}</p>
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
		.text-2xl { font-size: 1.5rem; }
		.text-lg { font-size: 1.125rem; }
		th, td { font-size: 0.75rem; padding: 0.5rem; }
	}
</style>
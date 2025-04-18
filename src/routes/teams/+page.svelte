<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');
	let loading = true;
	let errorMessages = [];
	let successMessage = '';
	let teamsContext = false;
	let teamsMobile = false;

	// Detect if the user is in a Teams context
	const isTeamsContext = () => {
		const userAgent = navigator.userAgent.toLowerCase();
		const isTeams = userAgent.includes("teams");
		const isEmbedded = 
			(window.parent === window.self && window.nativeInterface) ||
			window.name === "embedded-page-container" ||
			window.name === "extension-tab-frame";
		return isTeams || isEmbedded;
	};

	// Detect if the user is on Teams mobile
	const isTeamsMobile = () => {
		const userAgent = navigator.userAgent.toLowerCase();
		const isTeams = userAgent.includes("teams");
		const isMobile = /mobile|android|iphone|ipad|ipod/.test(userAgent);
		const isTeamsMobileApp = userAgent.includes("com.microsoft.skype.teams") || userAgent.includes("teamsmobile");
		return isTeams && isMobile && isTeamsMobileApp;
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			if (sessionUser.token) localStorage.token = sessionUser.token;
			await user.set(sessionUser);
			if (teamsContext && typeof window.microsoftTeams !== 'undefined') {
				window.microsoftTeams.appInitialization.notifySuccess();
			}
			// Show success banner and redirect to /
			successMessage = $i18n.t('Connection successful!');
			setTimeout(() => {
				const redirectUrl = '/';
				if (typeof redirectUrl !== 'string') {
					const error = $i18n.t('Invalid redirect URL');
					errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
					return;
				}
				goto(redirectUrl);
			}, 2000);
		}
	};

	const waitForTeamsSDK = (callback, timeout = 10000) => {
		const startTime = Date.now();
		function checkSDK() {
			if (typeof window.microsoftTeams !== 'undefined') {
				callback();
			} else if (Date.now() - startTime < timeout) {
				setTimeout(checkSDK, 100);
			} else {
				const error = $i18n.t('Failed to initialize Teams SDK');
				errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
				loading = false;
			}
		}
		checkSDK();
	};

	const tryTeamsAuth = async (token, retryCount = 0, maxRetries = 3) => {
		try {
			const response = await fetch('/api/teams/auth', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
				body: JSON.stringify({ token })
			});
			const contentType = response.headers.get('content-type') || 'unknown';
			const status = response.status;

			// Retry on 502
			if (status === 502 && retryCount < maxRetries) {
				const error = $i18n.t(`HTTP 502: Retrying (${retryCount + 1}/${maxRetries})`);
				errorMessages = [...errorMessages, { status, message: error, timestamp: new Date().toISOString() }];
				await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
				return await tryTeamsAuth(token, retryCount + 1, maxRetries);
			}

			// Handle errors
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

			// Handle JSON response
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
			return false;
		}
	};

	onMount(async () => {
		// Detect Teams context and mobile
		teamsContext = isTeamsContext();
		teamsMobile = isTeamsMobile();

		if ($user) {
			// Already authenticated, redirect to /
			const redirectUrl = '/';
			if (typeof redirectUrl !== 'string') {
				const error = $i18n.t('Invalid redirect URL');
				errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
				return;
			}
			goto(redirectUrl);
			return;
		}

		if (!teamsContext) {
			// Not in Teams context, redirect to /auth
			const redirectUrl = '/auth';
			if (typeof redirectUrl !== 'string') {
				const error = $i18n.t('Invalid redirect URL');
				errorMessages = [...errorMessages, { status: 'N/A', message: error, timestamp: new Date().toISOString() }];
				return;
			}
			goto(redirectUrl);
			return;
		}

		waitForTeamsSDK(() => {
			try {
				window.microsoftTeams.initialize();
				window.microsoftTeams.appInitialization.notifyAppLoaded();

				window.microsoftTeams.authentication.getAuthToken({
					successCallback: async (token) => {
						await tryTeamsAuth(token);
					},
					failureCallback: (error) => {
						const errMsg = $i18n.t(`Authentication failed: ${error}`);
						errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
						loading = false;
					}
				});
			} catch (error) {
				const errMsg = $i18n.t(`Teams SDK initialization error: ${error.message}`);
				errorMessages = [...errorMessages, { status: 'N/A', message: errMsg, timestamp: new Date().toISOString() }];
				loading = false;
			}
		});
	});
</script>

<div class="w-full h-screen flex flex-col items-center justify-center p-4 space-y-4">
	{#if successMessage}
		<div class="w-full bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 p-4 rounded">
			<h2 class="text-lg font-semibold mb-2">{$i18n.t('Success')}</h2>
			<p class="text-sm">{$i18n.t(successMessage)}</p>
		</div>
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

	{#if loading}
		<div class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Authenticating...')}</div>
	{/if}
</div>

<style>
	/* Ensure table is responsive */
	.min-w-full {
		width: 100%;
	}
	.overflow-x-auto {
		overflow-x: auto;
	}
	/* Table styling */
	table {
		border-collapse: collapse;
	}
	th, td {
		text-align: left;
	}
	/* Flexible message column */
	.break-words {
		word-break: break-word;
	}
	/* Responsive adjustments */
	@media (max-width: 640px) {
		.text-2xl {
			font-size: 1.5rem;
		}
		.text-lg {
			font-size: 1.125rem;
		}
		th, td {
			font-size: 0.75rem;
			padding: 0.5rem;
		}
	}
</style>
<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');
	let loading = true;
	let errorMessage = '';
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
					errorMessage = $i18n.t('Invalid redirect URL');
					return;
				}
				goto(redirectUrl);
			}, 2000); // Redirect after 2 seconds
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
				errorMessage = $i18n.t('Failed to initialize Teams SDK');
				loading = false;
			}
		}
		checkSDK();
	};

	const tryTeamsAuth = async (token) => {
		try {
			const redirectUri = `${window.location.origin}/oauth/microsoft/callback`;
			const response = await fetch('/api/teams/auth', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ token, redirect_uri: redirectUri })
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail);
			}
			const sessionUser = await response.json();
			await setSessionUser(sessionUser);
			return true;
		} catch (error) {
			errorMessage = $i18n.t(`Authentication failed: ${error.message}`);
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
				errorMessage = $i18n.t('Invalid redirect URL');
				return;
			}
			goto(redirectUrl);
			return;
		}

		if (!teamsContext) {
			// Not in Teams context, redirect to /auth
			const redirectUrl = '/auth';
			if (typeof redirectUrl !== 'string') {
				errorMessage = $i18n.t('Invalid redirect URL');
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
						errorMessage = $i18n.t(`Authentication failed: ${error}`);
						loading = false;
					}
				});
			} catch (error) {
				errorMessage = $i18n.t(`Teams SDK initialization error: ${error.message}`);
				loading = false;
			}
		});
	});
</script>

<div class="w-full h-screen flex flex-col items-center justify-center p-4 space-y-4">
	{#if successMessage}
		<div class="w-full sm:max-w-md bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 p-4 rounded">
			<h2 class="text-lg font-semibold mb-2">{$i18n.t('Success')}</h2>
			<p class="text-sm">{successMessage}</p>
		</div>
	{/if}

	{#if errorMessage}
		<div class="w-full sm:max-w-md bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded">
			<h2 class="text-lg font-semibold mb-2">{$i18n.t('Error')}</h2>
			<p class="text-sm">{errorMessage}</p>
		</div>
	{/if}

	{#if loading}
		<div class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Authenticating...')}</div>
	{/if}
</div>

<style>
	/* Ensure buttons and text scale appropriately */
	@media (max-width: 640px) {
		.text-2xl {
			font-size: 1.5rem;
		}
		.text-lg {
			font-size: 1.125rem;
		}
	}
</style>
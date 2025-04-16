<script>
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { getSessionUser } from '$lib/apis/auths';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');
	let loading = true;
	let showPopup = false;
	let accounts = [];

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			if (sessionUser.token) localStorage.token = sessionUser.token;
			await user.set(sessionUser);
			if (typeof window.microsoftTeams !== 'undefined') {
				window.microsoftTeams.appInitialization.notifySuccess();
			}
			goto('/');
		}
	};

	const waitForTeamsSDK = (callback, timeout = 5000) => {
		const startTime = Date.now();
		function checkSDK() {
			if (typeof window.microsoftTeams !== 'undefined') {
				callback();
			} else if (Date.now() - startTime < timeout) {
				setTimeout(checkSDK, 100);
			} else {
				console.log('DEBUG: Teams SDK failed to load');
				fetchOAuthUrl();
			}
		}
		checkSDK();
	};

	const fetchOAuthUrl = async () => {
		loading = true;
		try {
			const redirectUri = window.location.origin + '/oauth/microsoft/callback';
			const response = await fetch(`/api/oauth/microsoft/login-url?redirect_uri=${encodeURIComponent(redirectUri)}`, {
				method: 'GET',
				headers: { 'Content-Type': 'application/json' }
			});
			if (!response.ok) throw new Error('Failed to get OAuth URL');
			const data = await response.json();
			accounts = [{
				id: 'manual',
				displayName: $i18n.t('Sign in with Microsoft'),
				email: $i18n.t('Select to authenticate'),
				oauthUrl: data.url
			}];
			await fetch('/api/set-redirect', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ redirect: window.location.origin + '/' })
			});
			console.log('DEBUG: OAuth URL fetched:', data.url);
			await tick(); // Ensure UI updates
			showPopup = true;
		} catch (error) {
			console.error('DEBUG: OAuth URL fetch error:', error);
			toast.error($i18n.t('Failed to load sign-in URL'));
			loading = false;
			showPopup = false;
		}
	};

	const tryTeamsAuth = async (token) => {
		try {
			const redirectUri = window.location.origin + '/oauth/microsoft/callback';
			const response = await fetch('/api/teams/auth', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ token, redirect_uri: redirectUri })
			});
			if (!response.ok) {
				const errorData = await response.json();
				if (errorData.detail.includes('AADSTS50020')) {
					console.log('DEBUG: Multiple accounts detected');
					fetchOAuthUrl();
					return false;
				}
				throw new Error('Authentication failed');
			}
			const sessionUser = await response.json();
			await setSessionUser(sessionUser);
			return true;
		} catch (error) {
			console.error('DEBUG: Teams auth error:', error);
			fetchOAuthUrl();
			return false;
		}
	};

	const selectAccount = async (account) => {
		if (!account) return;
		loading = true;
		showPopup = false;
		console.log('DEBUG: Selecting account:', account.id);
		if (account.id === 'manual') {
			try {
				if (typeof window.microsoftTeams !== 'undefined') {
					console.log('DEBUG: Attempting Teams authentication dialog');
					window.microsoftTeams.initialize();
					window.microsoftTeams.authentication.authenticate({
						url: account.oauthUrl,
						width: 600,
						height: 600,
						isExternal: true, // Force external popup
						successCallback: () => {
							console.log('DEBUG: Authentication dialog succeeded');
							goto('/');
						},
						failureCallback: (error) => {
							console.error('DEBUG: Authentication dialog failed:', error);
							// Fallback to top-level navigation
							console.log('DEBUG: Falling back to top-level navigation');
							window.top.location.href = account.oauthUrl;
						}
					});
				} else {
					console.log('DEBUG: No Teams SDK, using top-level navigation');
					window.top.location.href = account.oauthUrl;
				}
			} catch (error) {
				console.error('DEBUG: Manual auth error:', error);
				toast.error($i18n.t('Authentication failed'));
				loading = false;
				fetchOAuthUrl();
			}
			return;
		}
		const success = await tryTeamsAuth(account.token);
		if (success) {
			loading = false;
		}
	};

	onMount(async () => {
		console.log('DEBUG: Teams context:', window.parent !== window, window.location.hostname);
		if ($user) {
			goto('/');
			return;
		}

		const isTeamsContext =(window.parent === window.self && window.nativeInterface) 
			|| window.navigator.userAgent.includes("Teams") 
			|| window.name === "embedded-page-container" 
			|| window.name === "extension-tab-frame";

		if (!isTeamsContext) {
			fetchOAuthUrl();
			return;
		}

		waitForTeamsSDK(() => {
			try {
				window.microsoftTeams.initialize();
				window.microsoftTeams.appInitialization.notifyAppLoaded();

				window.microsoftTeams.authentication.getAuthToken({
					successCallback: async (token) => {
						accounts = [{
							id: 'teams',
							displayName: $i18n.t('Teams Account'),
							email: $i18n.t('Use Teams authentication'),
							token
						}];
						const success = await tryTeamsAuth(token);
						if (!success) {
							await tick();
							showPopup = true;
						}
						loading = false;
					},
					failureCallback: (error) => {
						console.error('DEBUG: getAuthToken failed:', error);
						fetchOAuthUrl();
					}
				});
			} catch (error) {
				console.error('DEBUG: Teams SDK initialization error:', error);
				fetchOAuthUrl();
			}
		});
	});
</script>

<div class="w-full h-screen flex flex-col items-center justify-center p-4">
	<h1 class="text-2xl font-bold mb-4">{$i18n.t('Sign in to Teams')}</h1>
	<p class="text-gray-600 dark:text-gray-300 mb-6 text-center">
		{$i18n.t('Please choose an account to continue.')}
	</p>
	{#if loading}
		<div class="text-gray-600 dark:text-gray-300">{$i18n.t('Authenticating...')}</div>
	{:else}
		<button
			on:click={() => (showPopup = true)}
			class="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-blue-400"
			disabled={loading || accounts.length === 0}
		>
			{$i18n.t('Select Account')}
		</button>
	{/if}

	{#if showPopup}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
				<h2 class="text-xl font-semibold mb-4">{$i18n.t('Choose an Account')}</h2>
				{#if accounts.length > 0}
					<ul class="space-y-2">
						{#each accounts as account}
							<li>
								<button
									on:click={() => selectAccount(account)}
									class="w-full text-left px-4 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
									disabled={loading}
								>
									<span class="font-medium">{account.displayName}</span>
									<br />
									<span class="text-sm text-gray-500">{account.email}</span>
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-gray-600 dark:text-gray-300">{$i18n.t('No accounts available.')}</p>
				{/if}
				<div class="mt-4 flex justify-end">
					<button
						on:click={() => (showPopup = false)}
						class="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white"
						disabled={loading}
					>
						{$i18n.t('Cancel')}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	button {
		transition: background-color 0.2s;
	}
	.fixed {
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.bg-white {
		max-height: 80vh;
		overflow-y: auto;
	}
</style>
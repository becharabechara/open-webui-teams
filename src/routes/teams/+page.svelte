<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getSessionUser } from '$lib/apis/auths';
	import { user } from '$lib/stores';

	let loading = true;

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
				toast.error('Unable to initialize Teams authentication');
				escapeIframe();
			}
		}
		checkSDK();
	};

	const escapeIframe = () => {
		if (window.top === window) {
			window.location.href = '/oauth/microsoft/login';
		} else if (typeof window.microsoftTeams !== 'undefined') {
			window.microsoftTeams.authentication.authenticate({
				url: window.location.origin + '/oauth/microsoft/login',
				successCallback: () => {},
				failureCallback: () => {
					window.open(window.location.origin + '/oauth/microsoft/login', '_top');
				}
			});
		} else {
			window.open(window.location.origin + '/oauth/microsoft/login', '_top');
		}
	};

	const authenticateWithTeams = async () => {
		waitForTeamsSDK(() => {
			window.microsoftTeams.initialize(() => {
				// Signal tab is loaded
				window.microsoftTeams.appInitialization.notifyAppLoaded();

				window.microsoftTeams.authentication.getAuthToken({
					successCallback: async (token) => {
						try {
							const response = await fetch('/api/teams/auth', {
								method: 'POST',
								headers: { 'Content-Type': 'application/json' },
								body: JSON.stringify({ token })
							});
							if (!response.ok) throw new Error('Authentication failed');
							const sessionUser = await response.json();
							await setSessionUser(sessionUser);
						} catch {
							toast.error('Teams authentication failed');
							escapeIframe();
						}
					},
					failureCallback: () => {
						toast.error('Teams authentication failed');
						escapeIframe();
					}
				});
			});
		});
	};

	onMount(async () => {
		if ($user) {
			goto('/');
			return;
		}

		const isTeamsContext =
			window.parent !== window ||
			window.location.hostname.includes('teams.microsoft.com');

		if (isTeamsContext) {
			await authenticateWithTeams();
		} else {
			goto('/auth');
		}
		loading = false;
	});
</script>

<div class="w-full h-screen flex items-center justify-center">
	{#if loading}
		<div class="text-gray-600 dark:text-gray-300">Authenticating...</div>
	{/if}
</div>

<style>
	div {
		font-size: 1.2rem;
	}
</style>
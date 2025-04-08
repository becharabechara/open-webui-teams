<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import { getSessionUser } from '$lib/apis/auths';
  import { user } from '$lib/stores';

  // Log immediately when script loads
  console.log('[Teams Auth] Script loaded');
  window.alert('[Teams Auth] Script loaded');
  if (typeof document !== 'undefined') {
    const debugDiv = document.createElement('div');
    debugDiv.id = 'debug';
    debugDiv.style.position = 'absolute';
    debugDiv.style.top = '10px';
    debugDiv.style.left = '10px';
    debugDiv.style.background = 'yellow';
    debugDiv.style.padding = '10px';
    debugDiv.textContent = '[Teams Auth] Script loaded';
    document.body.appendChild(debugDiv);
  }

  let loading = true;

  const log = (message) => {
    const fullMessage = `[Teams Auth] ${message}`;
    console.log(fullMessage);
    window.alert(fullMessage);
    if (document.getElementById('debug')) {
      document.getElementById('debug').textContent += `\n${fullMessage}`;
    }
  };

  const setSessionUser = async (sessionUser) => {
    if (sessionUser) {
      log('Session user set: ' + JSON.stringify(sessionUser));
      if (sessionUser.token) localStorage.token = sessionUser.token;
      await user.set(sessionUser);
      goto('/');
    }
  };

  const waitForTeamsSDK = (callback, timeout = 5000) => {
    log('Starting waitForTeamsSDK');
    const startTime = Date.now();
    function checkSDK() {
      if (typeof microsoftTeams !== 'undefined') {
        log('Teams SDK detected, calling callback');
        callback();
      } else if (Date.now() - startTime < timeout) {
        log('Waiting for Teams SDK...');
        setTimeout(checkSDK, 100);
      } else {
        log('Teams SDK timeout after ' + timeout + 'ms');
        toast.error('Teams SSO unavailable, redirecting to login');
        escapeIframe();
      }
    }
    checkSDK();
  };

  const escapeIframe = () => {
    log('Attempting to escape iframe');
    if (window.top === window) {
      log('Not in iframe, redirecting directly');
      window.location.href = '/oauth/microsoft/login';
    } else if (typeof microsoftTeams !== 'undefined') {
      log('Using Teams authenticate to redirect');
      microsoftTeams.authentication.authenticate({
        url: window.location.origin + '/oauth/microsoft/login',
        successCallback: () => log('External auth completed'),
        failureCallback: (error) => {
          log('Teams authenticate failed: ' + error);
          window.open(window.location.origin + '/oauth/microsoft/login', '_top');
        },
      });
    } else {
      log('No Teams SDK, forcing top-level redirect');
      window.open(window.location.origin + '/oauth/microsoft/login', '_top');
    }
  };

  const authenticateWithTeams = async () => {
    log('Attempting Teams authentication');
    waitForTeamsSDK(() => {
      log('Teams SDK initialized');
      microsoftTeams.initialize(() => {
        log('SDK initialization complete');
        microsoftTeams.authentication.getAuthToken({
          successCallback: async (token) => {
            log('Token received: [redacted]');
            try {
              const response = await fetch('/api/teams/auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token }),
              });
              if (!response.ok) throw new Error('Authentication failed: ' + response.statusText);
              const sessionUser = await response.json();
              await setSessionUser(sessionUser);
            } catch (error) {
              log('Error during Teams auth: ' + error.message);
              toast.error('Teams authentication failed');
              escapeIframe();
            }
          },
          failureCallback: (error) => {
            log('Teams SSO failed: ' + error);
            toast.error('Teams SSO failed');
            escapeIframe();
          },
        });
      });
    });
  };

  onMount(async () => {
    log('onMount triggered');
    if ($user) {
      log('User already authenticated, redirecting to /');
      goto('/');
      return;
    }

    const isTeamsContext = window.parent !== window || window.location.hostname.includes('teams.microsoft.com');
    log('Is in Teams context: ' + isTeamsContext);
    log('window.parent !== window: ' + (window.parent !== window));
    log('hostname includes teams.microsoft.com: ' + window.location.hostname.includes('teams.microsoft.com'));
    if (isTeamsContext) {
      await authenticateWithTeams();
    } else {
      log('Not in Teams context, redirecting to standard login');
      goto('/auth');
    }
    loading = false;
  });
</script>

<div class="w-full h-screen flex items-center justify-center">
  {#if loading}
    <div>Authenticating with Teams...</div>
  {/if}
</div>
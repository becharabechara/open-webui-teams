<script>
	import { onMount, onDestroy } from 'svelte';
	const openWebUILogoLight = "/open-webui-favicon.png";
	const openWebUILogoDark = "/open-webui-favicon-dark.png";
	const openWebUIWebsite = "https://openwebui.com/";

	let isDarkMode = false;

	// Function to check the current theme
	const checkTheme = () => {
		isDarkMode = document.documentElement.classList.contains("dark");
	};

	onMount(() => {
		// Initial theme check
		checkTheme();

		// Set up a MutationObserver to detect theme changes
		const observer = new MutationObserver(() => {
			checkTheme();
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["class"],
		});

		return () => {
			observer.disconnect();
		};
	});
</script>

<a href={openWebUIWebsite} target="_blank" rel="noopener noreferrer" class="open-webui-link">
	<img src={isDarkMode ? openWebUILogoLight : openWebUILogoDark} alt="Open WebUI Logo" class="logo" />
	<span>Open WebUI</span>
</a>

<style>
	.open-webui-link {
		display: flex;
		align-items: center;
		text-decoration: none;
		/* Inherit text color from parent (text-gray-900 dark:text-gray-200) */
	}
	.logo {
		width: 1.125rem; /* 60% of UserMenu image (30px -> 18px) */
		height: 1.125rem;
		margin-right: 0.5rem; /* Reduced spacing to match smaller size */
	}
	span {
		font-family: inherit; /* Inherit font-primary from parent */
		font-weight: 500; /* Match font-medium */
		font-size: 0.625rem; /* Smaller than UserMenu text (14px -> 10px for readability) */
	}
</style>
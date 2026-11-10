<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket, theme } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	let submitting = false;

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (submitting) {
			return;
		}

		submitting = true;
		try {
			if (mode === 'ldap') {
				await ldapSignInHandler();
			} else if (mode === 'signin') {
				await signInHandler();
			} else {
				await signUpHandler();
			}
		} finally {
			submitting = false;
		}
	};

	const oauthCallbackHandler = async () => {
		function getCookie(name: string) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	const toggleTheme = () => {
		const isDark = document.documentElement.classList.contains('dark');
		const newTheme = isDark ? 'light' : 'dark';
		localStorage.setItem('theme', newTheme);
		theme.set(newTheme);
		if (isDark) {
			document.documentElement.classList.remove('dark');
			document.documentElement.classList.add('light');
		} else {
			document.documentElement.classList.remove('light');
			document.documentElement.classList.add('dark');
		}
	};

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		const logout = $page.url.searchParams.get('state') === 'logout';

		if ($user && !logout) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		// Auto-redirect to SSO when OAUTH_AUTO_REDIRECT is enabled and the
		// deployment is unambiguously SSO-only
		if ($config?.oauth?.auto_redirect && !logout && !form && !error) {
			const providers = Object.keys($config?.oauth?.providers ?? {});
			if (
				providers.length === 1 &&
				$config?.features?.auth !== false &&
				$config?.features?.enable_login_form === false &&
				!$config?.features?.enable_ldap &&
				!$config?.features?.auth_trusted_header &&
				!$config?.onboarding &&
				!localStorage.token &&
				!document.cookie.split('; ').some((c) => c.startsWith('token='))
			) {
				window.location.href = `${WEBUI_BASE_URL}/oauth/${providers[0]}/login`;
				return;
			}
		}

		loaded = true;

		if (($config?.features?.auth_trusted_header ?? false) || $config?.features?.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div
	class="relative min-h-screen w-full flex flex-col justify-between overflow-x-hidden bg-slate-50 dark:bg-[#070b14] text-slate-900 dark:text-slate-100 selection:bg-[#0066b0]/20 selection:text-[#0066b0] transition-colors duration-300"
	id="auth-page"
>
	<!-- Background Ambient Glow & Patterns -->
	<div class="pointer-events-none fixed inset-0 overflow-hidden z-0">
		<!-- Top-left OFPPT Green aura -->
		<div
			class="absolute -top-32 -left-32 size-[500px] rounded-full bg-[#0c8447]/10 dark:bg-[#0c8447]/15 blur-3xl"
		/>
		<!-- Bottom-right OFPPT Blue aura -->
		<div
			class="absolute -bottom-32 -right-32 size-[550px] rounded-full bg-[#0066b0]/10 dark:bg-[#0066b0]/20 blur-3xl"
		/>
		<!-- Center subtle ambient depth -->
		<div
			class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[650px] rounded-full bg-[#0066b0]/5 dark:bg-[#0066b0]/10 blur-[120px]"
		/>
		<!-- Subtle dot pattern -->
		<div
			class="absolute inset-0 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-40"
		/>
	</div>

	<!-- Top drag region for desktop apps -->
	<div class="w-full absolute top-0 left-0 right-0 h-6 drag-region z-20" />

	<!-- Top Navigation Header -->
	<header class="relative z-10 w-full px-5 py-4 flex items-center justify-between max-w-6xl mx-auto">
		<div class="flex items-center gap-2.5">
			<div
				class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 shadow-xs backdrop-blur-md"
			>
				<span class="inline-block size-2 rounded-full bg-[#0c8447] animate-pulse" />
				<span class="text-xs font-bold tracking-wider text-slate-800 dark:text-slate-100">OFPPT</span>
				<span class="text-[11px] text-slate-400 dark:text-slate-500 font-medium hidden sm:inline"
					>| Portail IA</span
				>
			</div>
		</div>

		<div class="flex items-center gap-2">
			<!-- Theme Toggle Button -->
			<button
				type="button"
				on:click={toggleTheme}
				class="size-9 flex items-center justify-center rounded-xl bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 text-slate-600 dark:text-slate-300 hover:text-[#0066b0] dark:hover:text-[#38bdf8] shadow-xs backdrop-blur-md transition-all active:scale-95"
				title="Changer de thème"
				aria-label="Basculer thème clair/sombre"
			>
				<!-- Sun icon in dark mode -->
				<svg
					class="size-4 hidden dark:block"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.8"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"
					/>
				</svg>
				<!-- Moon icon in light mode -->
				<svg
					class="size-4 block dark:hidden"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.8"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z"
					/>
				</svg>
			</button>
		</div>
	</header>

	<!-- Main Auth Content -->
	<main class="relative z-10 w-full flex-1 flex flex-col items-center justify-center px-4 py-6 sm:px-6">
		{#if loaded}
			{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
				<div
					class="w-full max-w-md p-8 rounded-3xl bg-white/95 dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800/90 shadow-2xl backdrop-blur-xl flex flex-col items-center justify-center text-center"
				>
					<div
						class="size-20 rounded-2xl bg-white dark:bg-slate-800 p-3 shadow-md border border-slate-100 dark:border-slate-700 mb-5 flex items-center justify-center"
					>
						<img
							src="{WEBUI_BASE_URL}/static/chat-nibras-logo.png"
							class="size-full object-contain"
							alt="Chat NIBRAS"
						/>
					</div>
					<div
						class="flex items-center gap-3 text-lg font-semibold text-slate-800 dark:text-slate-100"
					>
						<div>
							{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
						</div>
						<Spinner className="size-5 text-[#0066b0]" />
					</div>
				</div>
			{:else}
				<div
					id="auth-login-card"
					class="w-full max-w-[430px] rounded-3xl bg-white/95 dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800/90 shadow-[0_20px_50px_rgba(0,102,176,0.08)] dark:shadow-[0_25px_60px_rgba(0,0,0,0.55)] backdrop-blur-xl overflow-hidden transition-all duration-300"
				>
					<!-- Top OFPPT Gradient Bar -->
					<div class="h-1.5 w-full bg-gradient-to-r from-[#0c8447] via-[#0066b0] to-[#004f8c]" />

					<div class="p-6 sm:p-8">
						<!-- Card Header: Chat NIBRAS Logo & Title -->
						<div class="flex flex-col items-center text-center mb-6">
							<div class="relative mb-3 group">
								<div
									class="absolute -inset-2 rounded-2xl bg-gradient-to-r from-[#0c8447]/25 to-[#0066b0]/25 blur-lg opacity-75 group-hover:opacity-100 transition duration-300"
								/>
								<div
									class="relative h-20 sm:h-24 w-28 sm:w-32 rounded-2xl bg-white dark:bg-slate-800/95 p-2 shadow-sm border border-slate-100 dark:border-slate-700/80 flex items-center justify-center"
								>
									<!-- LICENSE covers this Open WebUI sign-in logo.
									Do not alter, remove, obscure, or replace it except as LICENSE permits:
									https://docs.openwebui.com/license. -->
									<img
										id="logo"
										crossorigin="anonymous"
										src="{WEBUI_BASE_URL}/static/chat-nibras-logo.png"
										class="size-full object-contain filter drop-shadow-xs"
										alt="{$WEBUI_NAME} logo"
										on:error={(e) => {
											e.currentTarget.src = `${WEBUI_BASE_URL}/static/favicon.png`;
										}}
									/>
								</div>
							</div>

							<!-- Institutional Badge -->
							<div
								class="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-[11px] font-semibold tracking-wider uppercase bg-emerald-50 dark:bg-emerald-950/40 text-[#0c8447] dark:text-emerald-400 border border-[#0c8447]/20 dark:border-emerald-800/40 mb-1.5"
							>
								<span class="size-1.5 rounded-full bg-[#0c8447] animate-pulse" />
								OFPPT • IA Institutionnelle
							</div>

							<!-- Main Name -->
							<h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
								Chat <span
									class="bg-gradient-to-r from-[#0066b0] to-[#0c8447] bg-clip-text text-transparent"
									>NIBRAS</span
								>
							</h1>

							<!-- Dynamic Subtitle -->
							<p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs">
								{#if $config?.onboarding ?? false}
									{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else if mode === 'ldap'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else if mode === 'signin'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else}
									{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{/if}
							</p>

							{#if $config?.onboarding ?? false}
								<div
									class="mt-2 text-[11px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700/60 leading-relaxed text-left"
								>
									ⓘ {$WEBUI_NAME}
									{$i18n.t(
										'does not make any external connections, and your data stays securely on your locally hosted server.'
									)}
								</div>
							{/if}
						</div>

						<!-- Auth Form -->
						<form
							class="flex flex-col"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
								<div class="space-y-3.5">
									<!-- Name Field (Sign Up) -->
									{#if mode === 'signup'}
										<div>
											<label
												for="name"
												class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5 text-left"
											>
												{$i18n.t('Name')}
											</label>
											<div
												class="relative flex items-center rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 focus-within:border-[#0066b0] focus-within:ring-2 focus-within:ring-[#0066b0]/20 transition-all"
											>
												<span class="pl-3.5 pr-1 text-slate-400 dark:text-slate-500 flex items-center">
													<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="1.8"
															d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
														/>
													</svg>
												</span>
												<input
													bind:value={name}
													type="text"
													id="name"
													class="w-full bg-transparent py-2.5 px-2.5 text-sm outline-hidden text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
													autocomplete="name"
													placeholder={$i18n.t('Enter Your Full Name')}
													required
												/>
											</div>
										</div>
									{/if}

									<!-- Username Field (LDAP) -->
									{#if mode === 'ldap'}
										<div>
											<label
												for="username"
												class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5 text-left"
											>
												{$i18n.t('Username')}
											</label>
											<div
												class="relative flex items-center rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 focus-within:border-[#0066b0] focus-within:ring-2 focus-within:ring-[#0066b0]/20 transition-all"
											>
												<span class="pl-3.5 pr-1 text-slate-400 dark:text-slate-500 flex items-center">
													<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="1.8"
															d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
														/>
													</svg>
												</span>
												<input
													bind:value={ldapUsername}
													type="text"
													class="w-full bg-transparent py-2.5 px-2.5 text-sm outline-hidden text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
													autocomplete="username"
													name="username"
													id="username"
													placeholder={$i18n.t('Enter Your Username')}
													required
												/>
											</div>
										</div>
									{:else}
										<!-- Email Field -->
										<div>
											<label
												for="email"
												class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5 text-left"
											>
												{$i18n.t('Email')}
											</label>
											<div
												class="relative flex items-center rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 focus-within:border-[#0066b0] focus-within:ring-2 focus-within:ring-[#0066b0]/20 transition-all"
											>
												<span class="pl-3.5 pr-1 text-slate-400 dark:text-slate-500 flex items-center">
													<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="1.8"
															d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
														/>
													</svg>
												</span>
												<input
													bind:value={email}
													type="email"
													id="email"
													class="w-full bg-transparent py-2.5 px-2.5 text-sm outline-hidden text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Your Email')}
													required
												/>
											</div>
										</div>
									{/if}

									<!-- Password Field -->
									<div>
										<label
											for="password"
											class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5 text-left"
										>
											{$i18n.t('Password')}
										</label>
										<div
											class="relative flex items-center rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 focus-within:border-[#0066b0] focus-within:ring-2 focus-within:ring-[#0066b0]/20 transition-all"
										>
											<span class="pl-3.5 pr-1 text-slate-400 dark:text-slate-500 flex items-center">
												<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="1.8"
														d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
													/>
												</svg>
											</span>
											<SensitiveInput
												bind:value={password}
												type="password"
												id="password"
												placeholder={$i18n.t('Enter Your Password')}
												autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
												name="password"
												screenReader={false}
												required
												aria-required="true"
												outerClassName="flex flex-1 items-center"
												class="w-full bg-transparent py-2.5 px-2.5 text-sm outline-hidden text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
												showButtonClassName="p-2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition"
											/>
										</div>
									</div>

									<!-- Confirm Password Field (Sign Up) -->
									{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
										<div>
											<label
												for="confirm-password"
												class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5 text-left"
											>
												{$i18n.t('Confirm Password')}
											</label>
											<div
												class="relative flex items-center rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 focus-within:border-[#0066b0] focus-within:ring-2 focus-within:ring-[#0066b0]/20 transition-all"
											>
												<span
													class="pl-3.5 pr-1 text-slate-400 dark:text-slate-500 flex items-center"
												>
													<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="1.8"
															d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
														/>
													</svg>
												</span>
												<SensitiveInput
													bind:value={confirmPassword}
													type="password"
													id="confirm-password"
													placeholder={$i18n.t('Confirm Your Password')}
													autocomplete="new-password"
													name="confirm-password"
													screenReader={false}
													required
													outerClassName="flex flex-1 items-center"
													class="w-full bg-transparent py-2.5 px-2.5 text-sm outline-hidden text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
													showButtonClassName="p-2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition"
												/>
											</div>
										</div>
									{/if}
								</div>
							{/if}

							<!-- Submit Button -->
							<div class="mt-5">
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<button
										type="submit"
										disabled={submitting}
										class="w-full py-2.5 sm:py-3 px-4 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-[#0066b0] to-[#00508e] hover:from-[#00569e] hover:to-[#004278] active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-[#0066b0]/25 hover:shadow-lg hover:shadow-[#0066b0]/35 transition-all flex items-center justify-center gap-2 cursor-pointer"
									>
										<span>
											{mode === 'ldap'
												? $i18n.t('Authenticate')
												: mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
										</span>

										{#if submitting}
											<Spinner className="size-4 text-white" />
										{/if}
									</button>

									<!-- Toggle Sign In / Sign Up -->
									{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
										<div
											class="mt-4 text-xs sm:text-sm text-center text-slate-500 dark:text-slate-400"
										>
											{mode === 'signin'
												? $i18n.t("Don't have an account?")
												: $i18n.t('Already have an account?')}

											<button
												class="ml-1 font-semibold text-[#0066b0] hover:text-[#005291] dark:text-[#38bdf8] dark:hover:text-sky-300 underline underline-offset-2 transition cursor-pointer"
												type="button"
												on:click={() => {
													mode = mode === 'signin' ? 'signup' : 'signin';
												}}
											>
												{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
											</button>
										</div>
									{/if}
								{/if}
							</div>
						</form>

						<!-- OAuth Providers Section -->
						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="relative my-5">
								<div class="absolute inset-0 flex items-center">
									<div class="w-full border-t border-slate-200 dark:border-slate-800" />
								</div>
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<div class="relative flex justify-center text-xs uppercase">
										<span
											class="bg-white dark:bg-slate-900 px-3 text-slate-400 dark:text-slate-500 font-medium tracking-wider"
										>
											{$i18n.t('or')}
										</span>
									</div>
								{/if}
							</div>

							<div class="flex flex-col space-y-2.5">
								{#if $config?.oauth?.providers?.google}
									<button
										class="flex justify-center items-center bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 shadow-xs hover:shadow-sm transition-all w-full rounded-xl font-medium text-sm py-2.5 cursor-pointer"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 48 48"
											class="size-5 mr-3"
											aria-hidden="true"
										>
											<path
												fill="#EA4335"
												d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
											/><path
												fill="#4285F4"
												d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
											/><path
												fill="#FBBC05"
												d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
											/><path
												fill="#34A853"
												d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
											/><path fill="none" d="M0 0h48v48H0z" />
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
									</button>
								{/if}

								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="flex justify-center items-center bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 shadow-xs hover:shadow-sm transition-all w-full rounded-xl font-medium text-sm py-2.5 cursor-pointer"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 21 21"
											class="size-5 mr-3"
											aria-hidden="true"
										>
											<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
												x="1"
												y="11"
												width="9"
												height="9"
												fill="#00a4ef"
											/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
												x="11"
												y="11"
												width="9"
												height="9"
												fill="#ffb900"
											/>
										</svg>
										<span
											>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
										>
									</button>
								{/if}

								{#if $config?.oauth?.providers?.github}
									<button
										class="flex justify-center items-center bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 shadow-xs hover:shadow-sm transition-all w-full rounded-xl font-medium text-sm py-2.5 cursor-pointer"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											class="size-5 mr-3"
											aria-hidden="true"
										>
											<path
												fill="currentColor"
												d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
									</button>
								{/if}

								{#if $config?.oauth?.providers?.oidc}
									<button
										class="flex justify-center items-center bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 shadow-xs hover:shadow-sm transition-all w-full rounded-xl font-medium text-sm py-2.5 cursor-pointer"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.8"
											stroke="currentColor"
											class="size-5 mr-3"
											aria-hidden="true"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>
										<span
											>{$i18n.t('Continue with {{provider}}', {
												provider: $config?.oauth?.providers?.oidc ?? 'SSO'
											})}</span
										>
									</button>
								{/if}

								{#if $config?.oauth?.providers?.feishu}
									<button
										class="flex justify-center items-center bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 shadow-xs hover:shadow-sm transition-all w-full rounded-xl font-medium text-sm py-2.5 cursor-pointer"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
										}}
									>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
									</button>
								{/if}
							</div>
						{/if}

						<!-- LDAP / Email Toggle -->
						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 text-center">
								<button
									class="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition py-1 px-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60 cursor-pointer"
									type="button"
									on:click={() => {
										if (mode === 'ldap') {
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										} else {
											mode = 'ldap';
										}
									}}
								>
									<span>
										{mode === 'ldap'
											? $i18n.t('Continue with Email')
											: $i18n.t('Continue with LDAP')}
									</span>
								</button>
							</div>
						{/if}

						<!-- Login Footer (Metadata / Admin Notice) -->
						{#if $config?.metadata?.login_footer}
							<div
								class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/60 text-[0.72rem] text-slate-400 dark:text-slate-500 marked text-center"
							>
								{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
							</div>
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	</main>

	<!-- Institutional Page Footer -->
	<footer
		class="relative z-10 w-full py-5 px-4 text-center text-xs text-slate-400 dark:text-slate-500 flex flex-col items-center gap-1 max-w-6xl mx-auto"
	>
		<div class="flex flex-wrap items-center justify-center gap-2 font-medium text-slate-600 dark:text-slate-400">
			<span class="font-bold text-[#0066b0] dark:text-[#38bdf8]">OFPPT</span>
			<span class="hidden sm:inline">•</span>
			<span class="text-xs">Office de la Formation Professionnelle et de la Promotion du Travail</span>
		</div>
		<div class="text-[11px] text-slate-400 dark:text-slate-600">
			Plateforme d'Intelligence Artificielle Souveraine et Sécurisée
		</div>
	</footer>
</div>

// TODO: this project has no authentication endpoint yet (Story 1.1 is
// scaffolding only — see the Architecture spine's `brain/settings_router/`,
// which will eventually own auth). Every member below is a structural
// placeholder so `merged-fixtures.ts` and any future auth-aware test
// type-check today. Wire `manageAuthToken` and the real cookie/localStorage
// names to the actual auth flow once a story introduces one, and delete
// these TODOs.
import { type AuthProvider } from '@seontechnologies/playwright-utils/auth-session';

const authProvider: AuthProvider = {
  getEnvironment: (options) => options.environment || process.env.TEST_ENV || 'local',

  getUserIdentifier: (options) => options.userIdentifier || 'default-user',

  extractToken: (storageState) => {
    // TODO: confirm storage mechanism (cookie vs localStorage) and the real
    // token entry name once an auth endpoint exists.
    return storageState.cookies.find((c) => c.name === 'auth_token')?.value;
  },

  extractCookies: (tokenData) => {
    // TODO: confirm cookie name/domain/security flags once a real auth
    // endpoint exists.
    return [
      {
        name: 'auth_token',
        value: tokenData,
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        secure: false,
      },
    ];
  },

  isTokenExpired: (storageState) => {
    const expiresAt = storageState.cookies.find((c) => c.name === 'expires_at');
    return Date.now() > parseInt(expiresAt?.value || '0', 10);
  },

  manageAuthToken: async () => {
    // TODO: implement once a real auth endpoint exists. Should return a
    // Playwright storage-state object per the auth-session provider contract.
    throw new Error(
      'auth-provider.manageAuthToken is not implemented yet — this project has no auth endpoint (see tests/support/auth-provider.ts).',
    );
  },
};

export default authProvider;

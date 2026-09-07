import { test as base } from '@playwright/test';
import { createAuthFixtures, setAuthProvider } from '@seontechnologies/playwright-utils/auth-session';
import authProvider from './auth-provider';

// Registered before the fixture is built, per auth-session.md's ordering rule.
setAuthProvider(authProvider);

export const test = base.extend(createAuthFixtures());

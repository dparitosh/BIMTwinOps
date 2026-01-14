import { AuthenticationClient } from '@aps_sdk/authentication';
import { parseScopes } from './apsScopes.js';
import { requiredEnv } from './config.js';

export function createTokenService({ config, store }) {
  const authenticationClient = new AuthenticationClient();

  async function getTwoLeggedToken() {
    const cacheKey = `aps:2l:${config.APS_CLIENT_ID}:${config.APS_SCOPES}`;
    const cached = await store.get(cacheKey);
    const now = Date.now();
    const safetyWindowMs = 30_000;

    if (cached?.access_token && cached?.expires_at && (cached.expires_at - safetyWindowMs) > now) {
      return cached;
    }

    const clientId = requiredEnv('APS_CLIENT_ID', config.APS_CLIENT_ID);
    const clientSecret = requiredEnv('APS_CLIENT_SECRET', config.APS_CLIENT_SECRET);
    const scopes = parseScopes(config.APS_SCOPES);

    const token = await authenticationClient.getTwoLeggedToken(clientId, clientSecret, scopes);
    const toCache = {
      access_token: token.access_token,
      token_type: token.token_type,
      expires_in: token.expires_in,
      expires_at: token.expires_at
    };

    // TTL a bit less than actual expiration to avoid edge expiry.
    const ttl = Math.max(30, Math.floor((token.expires_at - now) / 1000) - 30);
    await store.set(cacheKey, toCache, ttl);
    return toCache;
  }

  async function exchangeThreeLeggedCode({ code }) {
    const clientId = requiredEnv('APS_CLIENT_ID', config.APS_CLIENT_ID);
    const clientSecret = requiredEnv('APS_CLIENT_SECRET', config.APS_CLIENT_SECRET);
    const callbackUrl = requiredEnv('APS_CALLBACK_URL', config.APS_CALLBACK_URL);

    const token = await authenticationClient.getThreeLeggedToken(clientId, code, callbackUrl, { clientSecret });
    return {
      access_token: token.access_token,
      refresh_token: token.refresh_token,
      expires_at: token.expires_at,
      token_type: token.token_type
    };
  }

  async function refreshThreeLeggedToken({ refresh_token }) {
    const clientId = requiredEnv('APS_CLIENT_ID', config.APS_CLIENT_ID);
    const clientSecret = requiredEnv('APS_CLIENT_SECRET', config.APS_CLIENT_SECRET);
    const scopes = parseScopes(config.APS_OAUTH_SCOPES);

    const refreshed = await authenticationClient.refreshToken(refresh_token, clientId, { clientSecret, scopes });
    return {
      access_token: refreshed.access_token,
      refresh_token: refreshed.refresh_token || refresh_token,
      expires_at: refreshed.expires_at,
      token_type: refreshed.token_type
    };
  }

  return {
    getTwoLeggedToken,
    exchangeThreeLeggedCode,
    refreshThreeLeggedToken
  };
}

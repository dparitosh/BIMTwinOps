import { Scopes } from '@aps_sdk/authentication';

const scopeMap = {
  'user-profile:read': Scopes.UserProfileRead,
  'viewables:read': Scopes.ViewablesRead,
  'data:read': Scopes.DataRead,
  'data:search': Scopes.DataSearch,
  'data:write': Scopes.DataWrite,
  'data:create': Scopes.DataCreate,
  'data:validate': Scopes.DataValidate,
  'bucket:create': Scopes.BucketCreate,
  'bucket:read': Scopes.BucketRead,
  'bucket:update': Scopes.BucketUpdate,
  'bucket:delete': Scopes.BucketDelete,
  'code:all': Scopes.CodeAll,
  'account:read': Scopes.AccountRead,
  'account:write': Scopes.AccountWrite
};

export function parseScopes(raw) {
  const normalized = String(raw || '').trim();
  if (!normalized) return [Scopes.DataRead];

  const parts = normalized
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const unknown = parts.filter((s) => !scopeMap[s]);
  if (unknown.length) {
    const err = new Error(
      `Unknown APS scope(s): ${unknown.join(', ')}. ` +
      `Use a comma/space separated list like: data:read viewables:read bucket:create`
    );
    err.status = 400;
    throw err;
  }

  return parts.map((s) => scopeMap[s]);
}

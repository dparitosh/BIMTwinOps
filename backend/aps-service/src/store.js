import crypto from 'crypto';

export class MemoryStore {
  constructor() {
    this.map = new Map();
    this.timers = new Map();
  }

  async get(key) {
    return this.map.get(key) ?? null;
  }

  async set(key, value, ttlSeconds) {
    this.map.set(key, value);
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
      this.timers.delete(key);
    }
    if (ttlSeconds && ttlSeconds > 0) {
      const t = setTimeout(() => {
        this.map.delete(key);
        this.timers.delete(key);
      }, ttlSeconds * 1000);
      this.timers.set(key, t);
    }
  }

  async del(key) {
    this.map.delete(key);
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
      this.timers.delete(key);
    }
  }
}

export async function createStore({ type, redisUrl }) {
  if (type === 'redis') {
    const { createClient } = await import('redis');
    const client = createClient({ url: redisUrl });
    client.on('error', (err) => console.error('[Redis] error', err));
    await client.connect();

    return {
      kind: 'redis',
      async get(key) {
        const raw = await client.get(key);
        return raw ? JSON.parse(raw) : null;
      },
      async set(key, value, ttlSeconds) {
        const raw = JSON.stringify(value);
        if (ttlSeconds && ttlSeconds > 0) await client.set(key, raw, { EX: ttlSeconds });
        else await client.set(key, raw);
      },
      async del(key) {
        await client.del(key);
      }
    };
  }

  return { kind: 'memory', ...(new MemoryStore()) };
}

export function newId() {
  return crypto.randomUUID();
}

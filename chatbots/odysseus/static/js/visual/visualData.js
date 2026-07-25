// visualData.js — envelope/payload access for the visual stage.
// All network access goes through the odysseus proxy (/api/visual/<endpoint_id>/…);
// the browser never holds bridge tokens. Payloads are digest-verified (SubtleCrypto)
// and cached in memory by digest — immutable by contract.

const payloadCache = new Map(); // digest -> parsed payload

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// Stable JSON identical to the producer's _stable_json (sorted keys, compact separators).
function stableJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + stableJson(value[k])).join(',') + '}';
}

export async function verifyDigest(parsed, declared) {
  if (!declared || !declared.startsWith('sha256:')) return null; // nothing to verify against
  try {
    const actual = await sha256Hex(stableJson(parsed));
    return `sha256:${actual}` === declared;
  } catch {
    return null;
  }
}

// Build a fetchData(ref, envelope) function bound to a base URL resolver.
// resolveUrl(ref, envelope) -> URL string or null.
export function makeFetcher(resolveUrl, opts) {
  const strict = opts && opts.verify;
  return async function fetchData(ref, envelope) {
    if (!ref) return null;
    const cacheKey = ref.digest || null;
    if (cacheKey && payloadCache.has(cacheKey)) return payloadCache.get(cacheKey);
    const url = resolveUrl(ref, envelope);
    if (!url) return null;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`payload fetch ${res.status}`);
    const parsed = await res.json();
    if (cacheKey) {
      const ok = await verifyDigest(parsed, cacheKey);
      if (ok === false) {
        console.warn('digest mismatch for payload', ref.handle || url);
        if (strict) throw new Error('digest mismatch');
      }
      payloadCache.set(cacheKey, parsed);
    }
    return parsed;
  };
}

// ---- live proxy client (per conversation endpoint)
export class VisualClient {
  constructor(endpointId) {
    this.endpointId = endpointId;
    this.base = `/api/visual/${encodeURIComponent(endpointId)}`;
    this.fetchData = makeFetcher((ref, envelope) => {
      if (ref.kind === 'result_data' && ref.handle && envelope) {
        return `${this.base}/results/${encodeURIComponent(envelope.result_id)}/data/${encodeURIComponent(ref.handle)}`;
      }
      if (ref.kind === 'query' && ref.href) {
        // href is result-service-relative; route it through the proxy verbatim.
        return `${this.base}/passthrough?href=${encodeURIComponent(ref.href)}`;
      }
      return null;
    });
  }

  async capabilities() {
    const res = await fetch(`${this.base}/capabilities`);
    if (!res.ok) throw new Error(`capabilities ${res.status}`);
    return res.json();
  }

  async query(capabilityId, args, question) {
    const res = await fetch(`${this.base}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        capability_id: capabilityId,
        arguments: args || {},
        question: question || '',
      }),
    });
    if (!res.ok) throw new Error(`query ${res.status}`);
    return res.json();
  }

  async result(resultId) {
    const res = await fetch(`${this.base}/results/${encodeURIComponent(resultId)}`);
    if (!res.ok) throw new Error(`result ${res.status}`);
    return res.json();
  }
}

// ---- fixture client (dev/lab; also the offline fallback)
export function fixtureFetcher(baseUrl) {
  return makeFetcher((ref, envelope) => {
    if (ref.kind === 'result_data' && ref.handle && envelope) {
      const suffix = ref.media_type === 'application/geo+json' ? '.geojson' : '.json';
      return `${baseUrl}/data/${encodeURIComponent(envelope.result_id)}/${encodeURIComponent(ref.handle)}${suffix}`;
    }
    return null;
  });
}

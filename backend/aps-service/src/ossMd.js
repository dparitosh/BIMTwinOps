import multer from 'multer';
import { OssClient, PolicyKey, Region } from '@aps_sdk/oss';
import { ModelDerivativeClient } from '@aps_sdk/model-derivative';
import { base64UrlEncode } from './utils.js';

export function createUploadMiddleware() {
  // In-memory upload is fine for demo; for production, stream to disk/S3.
  return multer({ storage: multer.memoryStorage(), limits: { fileSize: 200 * 1024 * 1024 } });
}

function toRegion(value) {
  const v = String(value || 'US').toUpperCase();
  if (v === 'EMEA') return Region.Emea;
  if (v === 'APAC') return Region.Apac;
  return Region.Us;
}

export function createOssMdApi({ config, getAppAuthHeader, getUserAuthHeader }) {
  const oss = new OssClient();
  const md = new ModelDerivativeClient();

  async function getAuthHeader(auth = 'app') {
    if (auth === 'user') {
      if (!getUserAuthHeader) {
        const err = new Error('User auth is not configured on this server.');
        err.status = 500;
        throw err;
      }
      return await getUserAuthHeader();
    }
    return await getAppAuthHeader();
  }

  async function ensureBucket(bucketKey) {
    const region = toRegion(config.APS_OSS_REGION);
    try {
      await oss.getBucketDetails(bucketKey, { authorization: await getAppAuthHeader() });
      return { ok: true, bucketKey, existed: true };
    } catch {
      await oss.createBucket(region, { bucketKey, policyKey: PolicyKey.Transient }, { authorization: await getAppAuthHeader() });
      return { ok: true, bucketKey, existed: false };
    }
  }

  async function uploadObject({ bucketKey, objectKey, buffer }) {
    await ensureBucket(bucketKey);
    // SDK supports passing Buffer directly as sourceToUpload
    const resp = await oss.uploadObject(bucketKey, objectKey, buffer, { authorization: await getAppAuthHeader() });
    return resp;
  }

  function urnFromObjectId(objectId) {
    return base64UrlEncode(objectId);
  }

  async function translate({ urn, force = false, auth = 'app' }) {
    // Basic SVF2 translation request (viewer-friendly)
    const body = {
      input: { urn },
      output: {
        formats: [{ type: 'svf2', views: ['2d', '3d'] }]
      }
    };

    const resp = await md.translate(body, { authorization: await getAuthHeader(auth), xAdsForce: force });
    return resp;
  }

  async function manifest({ urn, auth = 'app' }) {
    return await md.getManifest(urn, { authorization: await getAuthHeader(auth) });
  }

  return {
    ensureBucket,
    uploadObject,
    urnFromObjectId,
    translate,
    manifest
  };
}

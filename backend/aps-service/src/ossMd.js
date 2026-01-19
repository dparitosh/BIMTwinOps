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
    const accessToken = (await getAppAuthHeader()).replace('Bearer ', '');
    console.log('[ensureBucket] bucketKey:', bucketKey, 'region:', region);
    try {
      // SDK: getBucketDetails(bucketKey, { accessToken })
      const details = await oss.getBucketDetails(bucketKey, { accessToken });
      console.log('[ensureBucket] exists:', details);
      return { ok: true, bucketKey, existed: true };
    } catch (err) {
      console.log('[ensureBucket] not found, creating...', err?.message);
      try {
        // SDK: createBucket(region, { bucketKey, policyKey }, { accessToken })
        const created = await oss.createBucket(region, { bucketKey, policyKey: PolicyKey.Transient }, { accessToken });
        console.log('[ensureBucket] created:', created);
        return { ok: true, bucketKey, existed: false };
      } catch (createErr) {
        console.error('[ensureBucket] create failed:', createErr);
        throw createErr;
      }
    }
  }

  async function uploadObject({ bucketKey, objectKey, buffer }) {
    console.log('[uploadObject] bucketKey:', bucketKey, 'objectKey:', objectKey, 'bufferSize:', buffer?.length);
    await ensureBucket(bucketKey);
    const accessToken = (await getAppAuthHeader()).replace('Bearer ', '');
    // SDK: uploadObject(bucketKey, objectKey, sourceToUpload, { accessToken })
    console.log('[uploadObject] calling oss.uploadObject...');
    const resp = await oss.uploadObject(bucketKey, objectKey, buffer, { accessToken });
    console.log('[uploadObject] response:', resp);
    return resp;
  }

  function urnFromObjectId(objectId) {
    return base64UrlEncode(objectId);
  }

  async function translate({ urn, force = false, auth = 'app' }) {
    // Basic SVF2 translation request (viewer-friendly)
    const jobPayload = {
      input: { urn },
      output: {
        formats: [{ type: 'svf2', views: ['2d', '3d'] }]
      }
    };
    
    const accessToken = (await getAuthHeader(auth)).replace('Bearer ', '');
    // SDK: startJob(jobPayload, { accessToken, xAdsForce })
    const resp = await md.startJob(jobPayload, { accessToken, xAdsForce: force });
    return resp;
  }

  async function manifest({ urn, auth = 'app' }) {
    const accessToken = (await getAuthHeader(auth)).replace('Bearer ', '');
    // SDK: getManifest(urn, { accessToken })
    return await md.getManifest(urn, { accessToken });
  }

  return {
    ensureBucket,
    uploadObject,
    urnFromObjectId,
    translate,
    manifest
  };
}

import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient } from '@defect-studio/api-client';
import { downloadPlanResultsZip, getResultFile, getResultMask, listResults, type ResultArtifact } from '.';

setupMswServer();

const BASE = 'http://bff.test';
const authedClient = () => new ApiClient({ baseUrl: BASE, token: 'access-abc' });

const RESULTS = `${BASE}/api/threads/thread-1/plans/0/results`;

const makeArtifact = (filename: string): ResultArtifact => ({
  id: `artifact-${filename}`,
  plan_id: '0',
  filename,
  file_type: 'image',
  file_size: null,
  created_at: '2026-08-21T05:49:32Z',
});

describe('listResults', () => {
  it('reads the artifacts of one plan', async () => {
    server.use(
      http.get(RESULTS, () =>
        HttpResponse.json({
          artifacts: [makeArtifact('0000.png'), makeArtifact('0001.png')],
          total: 2,
        }),
      ),
    );

    const res = await listResults(authedClient(), 'thread-1', '0');

    expect(res.total).toBe(2);
    expect(res.artifacts.map((a) => a.filename)).toEqual(['0000.png', '0001.png']);
  });

  it('sends the token', async () => {
    let auth: string | null = null;
    server.use(
      http.get(RESULTS, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ artifacts: [], total: 0 });
      }),
    );

    await listResults(authedClient(), 'thread-1', '0');

    expect(auth).toBe('Bearer access-abc');
  });

  it('reads an empty list for a plan that has not generated yet', async () => {
    server.use(http.get(RESULTS, () => HttpResponse.json({ artifacts: [], total: 0 })));

    const res = await listResults(authedClient(), 'thread-1', '0');

    expect(res).toEqual({ artifacts: [], total: 0 });
  });
});

describe('getResultFile', () => {
  it('reads the image bytes as a Blob', async () => {
    server.use(
      http.get(`${RESULTS}/0000.png`, () =>
        HttpResponse.arrayBuffer(new Uint8Array([137, 80, 78, 71]).buffer, {
          headers: { 'Content-Type': 'image/png' },
        }),
      ),
    );

    const blob = await getResultFile(authedClient(), 'thread-1', '0', '0000.png');

    expect(blob.size).toBe(4);
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(new Uint8Array([137, 80, 78, 71]));
  });

  it('escapes a filename with characters that would break the path', async () => {
    let path: string | null = null;
    server.use(
      http.get(`${RESULTS}/:filename`, ({ request }) => {
        path = new URL(request.url).pathname;
        return HttpResponse.arrayBuffer(new Uint8Array([1]).buffer);
      }),
    );

    await getResultFile(authedClient(), 'thread-1', '0', '스크린샷 001.png');

    expect(path).toBe(`/api/threads/thread-1/plans/0/results/${encodeURIComponent('스크린샷 001.png')}`);
  });
});

describe('getResultMask', () => {
  it('reads the mask bytes from the /mask path of the image', async () => {
    let path: string | null = null;
    server.use(
      http.get(`${RESULTS}/:filename/mask`, ({ request }) => {
        path = new URL(request.url).pathname;
        return HttpResponse.arrayBuffer(new Uint8Array([137, 80]).buffer, {
          headers: { 'Content-Type': 'image/png' },
        });
      }),
    );

    const blob = await getResultMask(authedClient(), 'thread-1', '0', '스크린샷 001.png');

    expect(blob.size).toBe(2);
    expect(path).toBe(`/api/threads/thread-1/plans/0/results/${encodeURIComponent('스크린샷 001.png')}/mask`);
  });

  it('rejects when the image has no mask', async () => {
    server.use(http.get(`${RESULTS}/0000.png/mask`, () => new HttpResponse(null, { status: 404 })));

    await expect(getResultMask(authedClient(), 'thread-1', '0', '0000.png')).rejects.toMatchObject({ status: 404 });
  });
});

describe('downloadPlanResultsZip', () => {
  it('downloads all images of a plan as a ZIP blob', async () => {
    server.use(
      http.get(`${RESULTS}/download`, () =>
        HttpResponse.arrayBuffer(new Uint8Array([80, 75, 3, 4]).buffer, {
          headers: { 'Content-Type': 'application/zip' },
        }),
      ),
    );

    const blob = await downloadPlanResultsZip(authedClient(), 'thread-1', '0');

    expect(blob.size).toBe(4);
    expect(blob.type).toBe('application/zip');
  });

  it('sends the token', async () => {
    let auth: string | null = null;
    server.use(
      http.get(`${RESULTS}/download`, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.arrayBuffer(new Uint8Array([1]).buffer, {
          headers: { 'Content-Type': 'application/zip' },
        });
      }),
    );

    await downloadPlanResultsZip(authedClient(), 'thread-1', '0');

    expect(auth).toBe('Bearer access-abc');
  });
});

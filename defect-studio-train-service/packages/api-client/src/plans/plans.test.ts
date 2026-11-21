import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient } from '@defect-studio/api-client';
import { listPlans, type Plan } from '.';

setupMswServer();

const BASE = 'http://bff.test';
const authedClient = () => new ApiClient({ baseUrl: BASE, token: 'access-abc' });

const PLANS = `${BASE}/api/threads/thread-1/plans`;

const makePlan = (planId: string): Plan => ({
  id: `row-${planId}`,
  plan_id: planId,
  content: { generation_count: 3, size: 'medium' },
  status: 'draft',
  created_at: '2026-08-21T05:28:50Z',
  updated_at: '2026-08-21T05:30:24Z',
});

describe('listPlans', () => {
  it('reads the plans of one thread', async () => {
    server.use(
      http.get(PLANS, () =>
        HttpResponse.json({ plans: [makePlan('0'), makePlan('1')], total: 2 }),
      ),
    );

    const res = await listPlans(authedClient(), 'thread-1');

    expect(res.total).toBe(2);
    expect(res.plans.map((p) => p.plan_id)).toEqual(['0', '1']);
  });

  it('keeps plan_id apart from the row id — the result endpoints key on plan_id', async () => {
    server.use(http.get(PLANS, () => HttpResponse.json({ plans: [makePlan('0')], total: 1 })));

    const [plan] = (await listPlans(authedClient(), 'thread-1')).plans;

    expect(plan.plan_id).toBe('0');
    expect(plan.id).toBe('row-0');
  });

  it('sends the token', async () => {
    let auth: string | null = null;
    server.use(
      http.get(PLANS, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ plans: [], total: 0 });
      }),
    );

    await listPlans(authedClient(), 'thread-1');

    expect(auth).toBe('Bearer access-abc');
  });

  it('reads an empty list for a thread with no plan yet', async () => {
    server.use(http.get(PLANS, () => HttpResponse.json({ plans: [], total: 0 })));

    expect(await listPlans(authedClient(), 'thread-1')).toEqual({ plans: [], total: 0 });
  });
});


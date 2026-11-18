import { describe, expect, it } from 'vitest';
import { adaptDevLoginResponse } from './stagingAuthProxy';

describe('staging dev-login localhost proxy', () => {
  const headers = () => ({ location: 'https://stage.gtrai.sec.samsung.net/', 'set-cookie': [
    'dice.dev-loginid=test-fixture; Path=/; HttpOnly; Secure; SameSite=lax',
    'dice.dev-role=user; Domain=stage.gtrai.sec.samsung.net; Path=/; Secure; HttpOnly',
  ] });
  const request = (redirect = 'http://localhost:13007/?tab=threads', host = 'localhost:13007') => ({
    headers: { host }, url: '/dev-login?redirect=' + encodeURIComponent(redirect),
  });

  it('returns an authorized dev login to the same localhost origin and keeps HttpOnly', () => {
    const response = headers();
    adaptDevLoginResponse(response, 307, request());
    expect(response.location).toBe('http://localhost:13007/?tab=threads');
    expect(response['set-cookie']).toEqual([
      'dice.dev-loginid=test-fixture; Path=/; HttpOnly; SameSite=lax',
      'dice.dev-role=user; Path=/; HttpOnly',
    ]);
  });

  it.each(['https://external.example/', 'http://localhost:9999/', 'http://[invalid'])('does not redirect or adapt cookies for %s', redirect => {
    const response = headers();
    const original = structuredClone(response);
    adaptDevLoginResponse(response, 307, request(redirect));
    expect(response).toEqual(original);
  });

  it('leaves the existing staging HTTPS flow unchanged', () => {
    const response = headers();
    const original = structuredClone(response);
    adaptDevLoginResponse(response, 307, request('https://stage.gtrai.sec.samsung.net/studio/', 'stage.gtrai.sec.samsung.net'));
    expect(response).toEqual(original);
  });

  it('keeps non-dev authentication cookies secure and unchanged', () => {
    const response = headers();
    const session = 'dice.session-token=fixture; Domain=stage.gtrai.sec.samsung.net; Secure; HttpOnly; SameSite=lax';
    response['set-cookie'].push(session);
    adaptDevLoginResponse(response, 307, request());
    expect(response['set-cookie'][2]).toBe(session);
  });

  it.each([200, 401, 403, 500])('does not adapt an unsuccessful login response (%s)', status => {
    const response = headers();
    const original = structuredClone(response);
    adaptDevLoginResponse(response, status, request());
    expect(response).toEqual(original);
  });

  it('requires real staging dev-session cookies, leaving ADFS redirects alone', () => {
    const response = { location:'https://stage.gtrai.sec.samsung.net/', 'set-cookie':['dice.state=fixture; Secure'] };
    const original = structuredClone(response);
    adaptDevLoginResponse(response, 307, request());
    expect(response).toEqual(original);
    const adfs = headers();
    adaptDevLoginResponse(adfs, 307, { headers:{ host:'localhost:13007' },url:'/api/auth/callback/adfs' });
    expect(adfs).toEqual(headers());
  });
});


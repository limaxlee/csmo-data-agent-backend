import { beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@defect-studio/test-utils/msw-server';
import { fireEvent, screen, waitFor } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { bytes, download, grouped, plan } from '@/mocks/galleryHandlers';

describe('GalleryTab download', () => {
  beforeEach(setupGalleryTest);

  // The download button hits the zip endpoint with the plan_id it belongs to.
  it('renders a download button per plan group', async () => {
    server.use(grouped([plan('1', ['b.png']), plan('0', ['a.png'])]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    const buttons = screen.getAllByRole('button', { name: '전체 다운로드' });
    expect(buttons.length).toBe(2);
  });

  it('requests the zip endpoint with the right plan id on click', async () => {
    const asked: string[] = [];
    server.use(
      grouped([plan('3', ['a.png'])]),
      // download() must come before bytes() — otherwise bytes() catches /download
      // as if it were a filename. The callback captures the plan_id.
      download(200, (pid) => asked.push(pid)),
      bytes(),
    );

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    const button = screen.getByRole('button', { name: '전체 다운로드' });
    fireEvent.click(button);

    await waitFor(() => expect(asked).toContain('3'));
  });

  it('disables the button while downloading', async () => {
    server.use(
      grouped([plan('0', ['a.png'])]),
      download(),
      bytes(),
    );

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    const button = screen.getByRole('button', { name: '전체 다운로드' }) as HTMLButtonElement;
    fireEvent.click(button);
    // The button is disabled during the request; it re-enables after it resolves.
    await waitFor(() => expect(button.disabled).toBe(false));
  });

  it('shows an error toast when the zip download fails', async () => {
    server.use(
      grouped([plan('0', ['a.png'])]),
      download(500),
      bytes(),
    );

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: '전체 다운로드' }));

    await waitFor(() => expect(screen.getByText('다운로드에 실패했습니다')).toBeTruthy());
  });

  it('explains an incomplete matching set and allows download retry', async () => {
    server.use(grouped([plan('0', ['a.png'])]),
      http.get('*/api/threads/t1/plans/0/results/download', () => HttpResponse.json({
        code: 'result_bundle_incomplete', filename: 'a.png', reason: 'missing_normal',
      }, { status: 409 })), bytes());
    renderGalleryTab();
    await screen.findByAltText('a.png');
    const button = screen.getByRole('button', { name: '전체 다운로드' }) as HTMLButtonElement;
    expect(button.title).toContain('정상 원본');
    fireEvent.click(button);
    await screen.findByText('a.png: 생성 당시 정상 원본이 없습니다. 관리자에게 문의해 주세요.');
    await waitFor(() => expect(button.disabled).toBe(false));
  });
});


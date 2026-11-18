import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@defect-studio/test-utils/react';
import { UploadTab } from './UploadTab';
vi.mock('@/features/train-data/ui/NativeImageTab', () => ({
  NativeImageTab: ({ category }: { category: string }) => <div aria-label="Native images">{category}</div>,
}));
describe('UploadTab', () => {
  it('uses native uploads without feature flags', () => {
    render(<UploadTab />);
    expect(screen.getByLabelText('Native images').textContent).toBe('defect');
  });
});

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@defect-studio/test-utils/react';
import { BackgroundTab } from './BackgroundTab';
vi.mock('@/features/train-data/ui/NativeImageTab', () => ({
  NativeImageTab: ({ category }: { category: string }) => <div aria-label="Native images">{category}</div>,
}));
describe('BackgroundTab', () => {
  it('uses native uploads without feature flags', () => {
    render(<BackgroundTab />);
    expect(screen.getByLabelText('Native images').textContent).toBe('normal');
  });
});
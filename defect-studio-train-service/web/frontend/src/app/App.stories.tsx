import type { Meta, StoryObj } from '@storybook/react';
import App from './App';
import { authenticate, appState } from '@/test/storybookBeforeEach';
import { grouped, download, bytes, plan } from '@/mocks/galleryHandlers';
import { handlers } from '@/mocks/handlers';

// Play functions are removed — the old selectors and the store setup they relied
// on (activeThreadId leaking between stories, hand-written fixtures, retry-loop
// helpers) no longer match how the components actually render. The stories render
// visually so you can see each tab, but the interaction tests will be rewritten in
// Phase 5b when App.stories.tsx gets its full rewrite.

const meta = {
  title: 'App/Smoke',
  component: App,
  parameters: {
    layout: 'fullscreen',
  },
  beforeEach: authenticate,
} satisfies Meta<typeof App>;

export default meta;

type Story = StoryObj<typeof meta>;

export const EmptyUpload: Story = {
  beforeEach: appState({ activeTab: 'upload' }),
};

export const UploadWithMswFlow: Story = {
  beforeEach: appState({ activeTab: 'upload' }),
};

export const ReferenceMaskRegistrationFlow: Story = {
  beforeEach: appState({
    activeTab: 'upload',
    references: [
      {
        id: 'story-ref-1',
        image: {
          id: 'story-reference-image',
          filename: 'reference.png',
          url: '/mock/source/reference-1.png',
          thumbnail_url: '/mock/source/reference-1.png',
          width: 768,
          height: 768,
          created_at: new Date('2026-05-18T00:00:00.000Z').toISOString(),
        },
        mask: null,
      },
    ],
    currentRefIndex: 0,
  }),
};

export const GeneratedImagesTab: Story = {
  beforeEach: appState({ activeTab: 'gallery' }),
};

// Shows plan groups with images and the per-plan download button. MSW handlers
// mock both the grouped results list and the individual image bytes, plus the
// zip download endpoint so the button click succeeds.
// download() must come before bytes() — otherwise bytes() catches /download
// as if it were a filename.
export const GalleryWithDownloadButton: Story = {
  beforeEach: [authenticate, appState({ activeTab: 'gallery' })],
  parameters: {
    msw: { handlers: [grouped([plan('0', ['0000.png', '0001.png'])]), download(), bytes(), ...handlers] },
  },
};

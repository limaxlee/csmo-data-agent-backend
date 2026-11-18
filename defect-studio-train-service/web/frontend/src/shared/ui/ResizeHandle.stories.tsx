import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { ResizeHandle } from './ResizeHandle';

const noop = () => {};

const meta = {
  title: 'Shared/ResizeHandle',
  component: ResizeHandle,
  args: {
    width: 320,
    min: 200,
    max: 600,
    label: '패널 너비 조절',
    onChange: noop,
  },
} satisfies Meta<typeof ResizeHandle>;

export default meta;

type Story = StoryObj<typeof meta>;

// The handle sits on the right edge of a panel, the way the conversation sidebar's
// does: the two panels touch with no gap and no rounded corners. Drag it or use
// ArrowLeft / ArrowRight to resize.
function SquareNoGapPanel({ width: initial, min, max, label }: {
  width: number;
  min: number;
  max: number;
  label: string;
}) {
  const [width, setWidth] = useState(initial);
  return (
    <>
      <div
        className="relative shrink-0 border-r border-gray-200 bg-gray-100 p-3 text-sm text-gray-600 dark:border-gray-800 dark:bg-dark-100 dark:text-gray-300"
        style={{ width }}
      >
        {width}px
        <ResizeHandle width={width} min={min} max={max}  label={label} />
      </div>
      <div className="flex-1 bg-gray-50 p-3 text-sm text-gray-400 dark:bg-dark-200 dark:text-gray-500">
        flex-1
      </div>
    </>
  );
}

export const SquareNoGap: Story = {
  decorators: [
    (Story) => (
      <div className="flex h-32 w-full">
        <Story />
      </div>
    ),
  ],
  render: (args) => <SquareNoGapPanel {...args} />,
};

// The handle fills the 16px gap left of the right panel, the way the image preview's
// does: gap-4 on the row, rounded corners, and no overflow-hidden on the parent (a
// clipped handle takes no clicks). `width` is the right panel's, so dragging left
// widens it.
function RoundedWithGapPanel({ width: initial, min, max, label, position, growsTo }: {
  width: number;
  min: number;
  max: number;
  label: string;
  position?: 'onRightEdge' | 'inLeftGap';
  growsTo?: 'right' | 'left';
}) {
  const [width, setWidth] = useState(initial);
  return (
    <>
      <div className="flex-1 rounded-lg bg-gray-50 p-3 text-sm text-gray-400 dark:bg-dark-200 dark:text-gray-500">
        flex-1
      </div>
      <div
        className="relative shrink-0 rounded-lg bg-gray-100 p-3 text-sm text-gray-600 dark:bg-dark-100 dark:text-gray-300"
        style={{ width }}
      >
        <ResizeHandle
          width={width}
          min={min}
          max={max}
          
          label={label}
          position={position}
          growsTo={growsTo}
        />
        {width}px
      </div>
    </>
  );
}

export const RoundedWithGap: Story = {
  args: { position: 'inLeftGap', growsTo: 'left' },
  decorators: [
    (Story) => (
      <div className="flex h-32 w-full gap-4">
        <Story />
      </div>
    ),
  ],
  render: (args) => <RoundedWithGapPanel {...args} />,
};


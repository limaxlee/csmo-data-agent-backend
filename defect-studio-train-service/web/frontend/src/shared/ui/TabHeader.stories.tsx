import type { Meta, StoryObj } from '@storybook/react';
import { TabHeader } from './TabHeader';

const meta = {
  title: 'Shared/TabHeader',
  component: TabHeader,
  args: {
    title: '정상 이미지',
    count: 3,
    description: '불량이 없는 제품 이미지로, 합성 배경으로 사용됩니다.',
  },
} satisfies Meta<typeof TabHeader>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
  args: { count: 0 },
};

export const Many: Story = {
  args: {
    count: 42,
    title: '불량 이미지',
    description: '합성에 사용할 불량 패턴이 담긴 이미지입니다.',
  },
};

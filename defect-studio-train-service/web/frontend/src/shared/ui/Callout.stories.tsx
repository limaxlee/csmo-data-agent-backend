import type { Meta, StoryObj } from '@storybook/react';
import { Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Callout } from './Callout';

const meta = {
  title: 'Shared/Callout',
  component: Callout,
  args: {
    children: '처리가 완료되었습니다.',
  },
} satisfies Meta<typeof Callout>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Info_: Story = {
  args: { tone: 'info', children: '이미지 3장이 업로드되었습니다.' },
};

export const Success: Story = {
  args: { tone: 'success', children: '학습이 완료되었습니다.' },
};

export const Warning: Story = {
  args: { tone: 'warning', children: '마스크를 등록하지 않은 불량 이미지가 있습니다.' },
};

export const Error_: Story = {
  args: { tone: 'error', children: '이미지 업로드에 실패했습니다.' },
};

export const WithIcon: Story = {
  args: {
    tone: 'info',
    icon: <Info size={16} />,
    children: '드래그 앤 드롭으로 이미지를 업로드할 수 있습니다.',
  },
};

export const WithIconSuccess: Story = {
  args: {
    tone: 'success',
    icon: <CheckCircle size={16} />,
    children: '마스크가 등록되었습니다.',
  },
};

export const WithIconWarning: Story = {
  args: {
    tone: 'warning',
    icon: <AlertTriangle size={16} />,
    children: '해상도가 낮은 이미지가 포함되어 있습니다.',
  },
};

export const WithIconError: Story = {
  args: {
    tone: 'error',
    icon: <XCircle size={16} />,
    children: '서버 연결에 실패했습니다.',
  },
};

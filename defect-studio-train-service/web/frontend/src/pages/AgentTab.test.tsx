import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { transferableAbortController } from 'node:util';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { renderWithUser, screen, waitFor } from '@defect-studio/test-utils/react';
import { Providers } from '@/app/Providers';
import { apiClient } from '@/shared/api/apiClient';
import { queryClient } from '@/shared/api/queryClient';
import { useAgentStore } from '@/features/agent-run/model/agentStore';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { ev, liveRunHandlers } from '@/mocks/liveRunHandlers';
import { makeThread } from '@/test/fixtures';
import { AgentTab } from './AgentTab';

// The list is virtualized with react-virtuoso, which needs a real layout to
// decide which items to mount; jsdom has none, so the items never appear. Render
// every item instead — the windowing itself is not what these tests assert.
vi.mock('react-virtuoso', () => ({
  Virtuoso: ({ data, itemContent, components }: {
    data: unknown[];
    itemContent: (index: number, item: unknown) => React.ReactNode;
    components?: { Footer?: () => React.ReactNode };
  }) => (
    <div data-testid="virtuoso-mock">
      {data.map((item, index) => itemContent(index, item))}
      {components?.Footer ? <components.Footer /> : null}
    </div>
  ),
}));

setupMswServer();
afterEach(() => vi.unstubAllGlobals());

// TrainDataBar, inside the composer, reads the train-data list with useQuery.
const renderTab = () => renderWithUser(<Providers><AgentTab /></Providers>);

const composer = () => screen.getByLabelText('에이전트 메시지 입력') as HTMLTextAreaElement;

describe('AgentTab', () => {
  beforeEach(() => {
    vi.stubGlobal('AbortController', transferableAbortController);
    queryClient.clear();
    apiClient.setToken('access-abc');
    apiClient.setTokenProvider(null);
    useActiveThreadStore.setState({ activeThreadId: null });
    useAgentStore.setState({ activeThreadId: null });
    useAgentStore.getState().resetSession();
    server.use(http.get('*/api/threads/:tid/native-data/activity', () => HttpResponse.json({ upload_in_progress: false })));
  });

  it('blocks sending for an upload started in another tab and preserves the draft', async () => {
    useActiveThreadStore.setState({ activeThreadId: 'thread-1' });
    useAgentStore.setState({ activeThreadId: 'thread-1' });
    server.use(http.get('*/api/threads/:tid/native-data/activity', () => HttpResponse.json({ upload_in_progress: true })));
    const { user } = renderTab();
    await screen.findByText(/이미지 업로드·검증 중에는 Agent 실행/);
    await user.type(composer(), '학습해 주세요{Enter}');
    expect(screen.getByRole('button', { name: '전송' })).toBeDisabled();
    expect(composer()).toHaveValue('학습해 주세요');
    expect(useAgentStore.getState().messages).toHaveLength(0);
    queryClient.setQueryData(['native-input-activity', 'thread-1'], { upload_in_progress: false });
    await waitFor(() => expect(screen.getByRole('button', { name: '전송' })).toBeEnabled());
    expect(composer()).toHaveValue('학습해 주세요');
  });

  it('creates a thread for the first message when none is open', async () => {
    server.use(
      http.post('*/api/threads', () => HttpResponse.json(makeThread('t9', null))),
      // TrainDataBar appears as soon as a thread is open and reads this list.
      http.get('*/api/threads/:tid/train-data', () => HttpResponse.json({ files: [], status: null })),
      ...liveRunHandlers([ev('agent.status', { message: '작업 중' })], true),
    );
    const { user } = renderTab();

    await user.type(composer(), '안녕');
    await user.click(screen.getByRole('button', { name: '전송' }));

    expect(await screen.findByText('안녕')).toBeTruthy(); // user bubble
    await waitFor(() => expect(useAgentStore.getState().activeThreadId).toBe('t9'));
    expect(useActiveThreadStore.getState().activeThreadId).toBe('t9');
    await waitFor(() => expect(useAgentStore.getState().status).toBe('작업 중'));
  });

  it('keeps the user message on screen and shows the error when the thread cannot be created', async () => {
    server.use(http.post('*/api/threads', () => new HttpResponse(null, { status: 500 })));
    const { user } = renderTab();

    await user.type(composer(), '안녕');
    await user.click(screen.getByRole('button', { name: '전송' }));

    expect(await screen.findByText('안녕')).toBeTruthy();
    await waitFor(() => expect(useAgentStore.getState().messages).toHaveLength(2));
    expect(useActiveThreadStore.getState().activeThreadId).toBeNull();
  });

  it('shows the heading above the input when no thread is open', () => {
    renderTab();

    expect(screen.getByText('무엇을 도와드릴까요?')).toBeTruthy();
  });

  it('shows the heading above the input on a thread with no messages', () => {
    useAgentStore.setState({ activeThreadId: 'thread-1' });
    renderTab();

    expect(screen.getByText('무엇을 도와드릴까요?')).toBeTruthy();
  });

  it('drops the heading once the thread has a message', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [{ id: 'u1', role: 'user', kind: 'text', text: '안녕' }],
    });
    renderTab();

    expect(screen.queryByText('무엇을 도와드릴까요?')).toBeNull();
  });

  it('drops the heading while a run with no messages yet is going', () => {
    useAgentStore.setState({ activeThreadId: 'thread-1', isRunning: true, runId: 'run-1' });
    renderTab();

    expect(screen.queryByText('무엇을 도와드릴까요?')).toBeNull();
  });

  it('keeps the input typable but shows only a stop button while a run is starting', () => {
    useAgentStore.setState({ activeThreadId: 'thread-1', consuming: true, isRunning: false, runId: 'run-1' });
    renderTab();

    expect(composer().disabled).toBe(false);
    expect(screen.getByRole('button', { name: '중지' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: '전송' })).toBeNull();
  });

  it('keeps the input open with a send button while a question waits', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      isRunning: true,
      consuming: true,
      awaitingInput: true,
    });
    renderTab();

    expect(composer().disabled).toBe(false);
    expect(screen.getByRole('button', { name: '전송' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: '중지' })).toBeNull();
  });

  it('draws markdown in agent text and leaves user text as typed', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [
        { id: 'a1', role: 'assistant', kind: 'text', text: '**굵게** 그리고 `코드`', markdown: true },
        { id: 'u1', role: 'user', kind: 'text', text: '**굵게**' },
      ],
    });
    const { container } = renderTab();

    expect(container.querySelector('strong')?.textContent).toBe('굵게');
    expect(container.querySelector('code')?.textContent).toBe('코드');
    expect(screen.getByText('**굵게**')).toBeTruthy(); // the user's text is untouched
  });

  it('hides the raw log lines until the log button is clicked', async () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [
        {
          id: 'p1',
          role: 'assistant',
          kind: 'progress',
          step: 'train/mask',
          label: '마스크 학습',
          state: 'running',
          percent: 30,
          logs: ['step 24 loss=0.031', 'step 25 loss=0.030'],
        },
      ],
    });
    const { user } = renderTab();

    expect(screen.queryByText(/step 24 loss/)).toBeNull();

    await user.click(screen.getByRole('button', { name: /로그 2줄/ }));
    expect(screen.getByText(/step 24 loss=0\.031/)).toBeTruthy();
  });

  it('shows a question as plain text, never as a button', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [{ id: 'q1', role: 'assistant', kind: 'confirm', prompt: '진행할까요?' }],
      isRunning: true,
      awaitingInput: true,
    });
    renderTab();

    expect(screen.getByText('진행할까요?')).toBeTruthy();
    expect(screen.queryByLabelText(/이 질문에 답변하기/)).toBeNull();
  });

  it('leaves out the spinning icon while the run waits at a question', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [{ id: 'q1', role: 'assistant', kind: 'confirm', prompt: '진행할까요?' }],
      isRunning: true,
      status: '계획 확인을 기다리는 중',
      awaitingInput: true,
    });
    const { container } = renderTab();

    expect(screen.getByText('계획 확인을 기다리는 중')).toBeTruthy();
    expect(container.querySelector('.animate-spin')).toBeNull();
  });

  it('keeps the spinning icon while the run is working', () => {
    useAgentStore.setState({
      activeThreadId: 'thread-1',
      messages: [{ id: 'a1', role: 'assistant', kind: 'text', text: '시작합니다' }],
      isRunning: true,
      status: '계획 세우는 중',
      awaitingInput: false,
    });
    const { container } = renderTab();

    expect(container.querySelector('.animate-spin')).toBeTruthy();
  });
});

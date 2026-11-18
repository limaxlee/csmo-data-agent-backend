import { useAgentStore } from '@/features/agent-run/model/agentStore';
import { AgentMessageList } from '@/features/agent-run/ui/AgentMessageList';
import { AgentInputRepairAction } from '@/features/agent-run/ui/AgentInputRepairAction';
import { AgentComposer } from '@/features/agent-run/ui/AgentComposer';
import { TrainDataBar } from '@/features/train-data/ui/TrainDataBar';
import { ConnectionNotice } from '@/features/agent-run/ui/ConnectionNotice';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { useNativeInputActivity } from '@/features/train-data/api/nativeData';
import { useUploadQueueStore, isFinished } from '@/features/train-data/model/uploadQueueStore';

export function AgentTab() {
  const thread = useActiveThreadStore((s) => s.activeThreadId);
  const localUpload = useUploadQueueStore((s) => s.batches.some((batch) =>
    (batch.thread ?? null) === thread && (!isFinished(batch) || batch.cleanup === 'running')));
  const activity = useNativeInputActivity(thread);
  const uploading = localUpload || Boolean(activity.data?.upload_in_progress);
  // Field selectors, not the whole store: a streamed token or a progress tick
  // replaces the store snapshot, so a whole-store subscription re-rendered this
  // page on every event. The children below are memo'd, so what still re-renders
  // here costs a vnode diff — but the selectors keep that work off idle events too.
  const messages = useAgentStore((s) => s.messages);
  const isRunning = useAgentStore((s) => s.isRunning);
  const consuming = useAgentStore((s) => s.consuming);
  const awaitingInput = useAgentStore((s) => s.awaitingInput);
  const stopping = useAgentStore((s) => s.cancelRequested);
  const cancelError = useAgentStore((s) => s.cancelError);
  const status = useAgentStore((s) => s.status);
  const runId = useAgentStore((s) => s.runId);
  const hasRunId = Boolean(runId);
  const cancelActiveRun = useAgentStore((s) => s.cancelActiveRun);
  const sendUserMessage = useAgentStore((s) => s.sendUserMessage);
  const connection = useAgentStore((s) => s.connection);

  // consuming is set before startRun returns, so a second send cannot be sent in the
  // time before run.started arrives. A run stopped at a question leaves the input open.
  const running = stopping || ((isRunning || consuming) && !awaitingInput);

  // A thread with nothing to read yet. A run reconnected by useShowActiveThread can have
  // no messages, and AgentMessageList shows its status line, so a run counts as content.
  const isEmpty = messages.length === 0 && !isRunning && !consuming;

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      <div
        className={`flex flex-col flex-1 min-w-0 w-full max-w-4xl mx-auto ${
          isEmpty ? 'justify-center' : ''
        }`}
      >
        {/* Left in place as an expression so AgentComposer stays the third child. React
            then keeps the same textarea when the list appears, along with its text and focus. */}
        {!isEmpty && (
          <AgentMessageList
            messages={messages}
            isRunning={isRunning}
            status={status}
            awaitingInput={awaitingInput}
            runId={runId}
          />
        )}

        {isEmpty && (
          <p className="px-3 pb-6 text-center text-3xl font-medium text-gray-900 dark:text-white">
            무엇을 도와드릴까요?
          </p>
        )}

        {(isRunning || consuming) && (
          <ConnectionNotice
            connection={connection}
            priorityMessage={
              cancelError ??
              (stopping && !['connected', 'idle'].includes(connection)
                ? '이전 요청이 중지됐는지 확인하지 못했습니다. 확인될 때까지 새 메시지를 보낼 수 없습니다.'
                : null)
            }
          />
        )}
        <AgentInputRepairAction />

        <AgentComposer
          uploading={uploading}
          running={running}
          stopping={stopping}
          canCancel={hasRunId}
          
          
          attachments={<TrainDataBar />}
        />
      </div>
    </div>
  );
}

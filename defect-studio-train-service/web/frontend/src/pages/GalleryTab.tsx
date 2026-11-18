import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, FolderOpen } from 'lucide-react';
import { useResults } from '@/features/results/api/useResults';
import { PlanGroup } from '@/features/results/ui/PlanGroup';
import { ResultPreviewPanel } from '@/features/results/ui/ResultPreviewPanel';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { useClickedImage } from '@/features/train-data/model/clickedImageStore';
import { ImageTabColumns } from '@/features/train-data/ui/ImageTabColumns';
import { errMsg, userErrorMessage } from '@/shared/api/errors';
import { logClientWarn } from '@/shared/lib/clientLogger';
import { Callout, TabHeader } from '@/shared/ui';

const Notice = ({ title, hint }: { title: string; hint?: string }) => (
  <div className="flex h-64 flex-col items-center justify-center text-gray-400">
    <FolderOpen size={48} className="mb-4 opacity-50" />
    <p className="text-lg">{title}</p>
    {hint && <p className="mt-2 text-sm">{hint}</p>}
  </div>
);

// The generated-images tab: one box per generation, newest first, each labelled
// with the plan it ran — how many images, where and how big the defect, and when
// it ran. The BFF indexes the images when the agent reports a finished
// generation, so a conversation that has not generated yet shows the empty
// state, not an error. Clicking an image opens it in the preview on the right.
export function GalleryTab() {
  const threadId = useActiveThreadStore((s) => s.activeThreadId);
  const { groups, total, isPending: pending, error } = useResults(threadId);
  // Every image in display order, so 이전/다음 steps from one generation to the next.
  const images = useMemo(() => groups.flatMap((group) => group.artifacts), [groups]);
  const { selected, select } = useClickedImage('generated', images);
  const [maskVisibility, setMaskVisibility] = useState<Record<string, boolean>>({});
  // Plan ids can repeat in different conversations; keep their visibility independent.
  const maskKey = (planId: string) => JSON.stringify([threadId, planId]);
  const showMaskFor = (planId: string) => maskVisibility[maskKey(planId)] ?? false;
  useEffect(() => {
    if (error && groups.length > 0) {
      logClientWarn('gallery.refresh_failed', { threadId, error: errMsg(error) });
    }
  }, [error, groups.length, threadId]);

  if (!threadId) {
    return <Notice title="대화를 선택해주세요" hint="왼쪽에서 대화를 열면 그 대화의 생성 이미지가 표시됩니다" />;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <TabHeader
        title="생성 이미지"
        count={total}
        description="불량 패턴을 정상 이미지에 합성한 결과입니다."
      />

      <ImageTabColumns
        previewOpen={!!selected}
        listHeader={
          error && groups.length === 0 && (
            <Callout tone="error" icon={<AlertTriangle size={16} />}>
              이미지 목록을 불러오지 못했습니다. {userErrorMessage(error, '잠시 후 다시 시도해 주세요.', 'gallery.load_failed')}
            </Callout>
          )
        }
        list={
          // Drawn whenever there is anything to draw, so a refetch that fails
          // leaves the images already on screen rather than blanking them.
          groups.length > 0 ? (
            <div className="flex flex-col gap-3">
              {groups.map((group) => (
                <PlanGroup
                  key={group.plan_id}
                  threadId={threadId}
                  group={group}
                  selectedId={selected?.id ?? null}
                  showMask={showMaskFor(group.plan_id)}
                   => setMaskVisibility((previous) => ({
                    ...previous,
                    [maskKey(group.plan_id)]: on,
                  }))}
                  onOpen={(image) => select(image.id)}
                />
              ))}
            </div>
          ) : (
            !error && (
              <Notice
                title={pending ? '불러오는 중…' : '생성 이미지가 없습니다'}
                hint={pending ? undefined : '이미지를 생성하면 여기에 표시됩니다'}
              />
            )
          )
        }
        preview={
          <ResultPreviewPanel
            threadId={threadId}
            images={images}
            selected={selected}
            
             => select(null)}
            showMask={selected ? showMaskFor(selected.plan_id) : false}
          />
        }
      />
    </div>
  );
}

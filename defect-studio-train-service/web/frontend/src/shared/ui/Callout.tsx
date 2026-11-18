import { cva, type VariantProps } from 'class-variance-authority';
import type { ReactNode } from 'react';

// Tinted, bordered callout box. Tones are full literal class strings (not
// interpolated) so Tailwind's purge keeps them in the build.
const callout = cva('rounded-lg border p-3 text-sm', {
  variants: {
    tone: {
      info: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
      success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300',
      warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300',
      error: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
    },
  },
  defaultVariants: {
    tone: 'info',
  },
});

interface CalloutProps extends VariantProps<typeof callout> {
  /** Optional leading icon; when present, content is laid out as an icon + body row. */
  icon?: ReactNode;
  children: ReactNode;
}

export function Callout({ tone, icon, children }: CalloutProps) {
  return (
    <div className={callout({ tone })}>
      {icon ? (
        <div className="flex items-start gap-2">
          <span className="mt-0.5 shrink-0">{icon}</span>
          <div>{children}</div>
        </div>
      ) : (
        children
      )}
    </div>
  );
}


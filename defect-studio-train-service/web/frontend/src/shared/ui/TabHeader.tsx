// Shared by all image tabs: title, inline image count, and a short description.
interface TabHeaderProps {
  title: string;
  count: number;
  description: string;
}

export function TabHeader({ title, count, description }: TabHeaderProps) {
  return (
    <div className="shrink-0">
      <h2 className="flex items-baseline gap-2 text-base font-semibold">
        {title}{' '}
        <span className="font-normal text-gray-400">{count}</span>
      </h2>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  );
}

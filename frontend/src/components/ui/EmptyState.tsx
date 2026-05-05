import Link from "next/link";

interface EmptyStateProps {
  message: string;
  cta?: { label: string; href: string };
}

export default function EmptyState({ message, cta }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <p className="text-gray-400 mb-4">{message}</p>
      {cta && (
        <Link
          href={cta.href}
          className="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light"
        >
          {cta.label}
        </Link>
      )}
    </div>
  );
}

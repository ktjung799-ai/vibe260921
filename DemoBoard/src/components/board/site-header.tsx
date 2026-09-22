import Link from "next/link";
import { MessageSquareText, SquarePen } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-semibold">
          <MessageSquareText className="size-5 text-primary" />
          DemoBoard
        </Link>
        <Button size="sm" nativeButton={false} render={<Link href="/posts/new" />}>
          <SquarePen data-icon="inline-start" />
          글쓰기
        </Button>
      </div>
    </header>
  );
}

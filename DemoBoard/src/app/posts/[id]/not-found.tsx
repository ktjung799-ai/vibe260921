import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function PostNotFound() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <h1 className="font-heading text-xl font-semibold">글을 찾을 수 없습니다</h1>
      <p className="text-sm text-muted-foreground">
        삭제되었거나 존재하지 않는 글입니다.
      </p>
      <Button nativeButton={false} render={<Link href="/" />}>
        목록으로 돌아가기
      </Button>
    </div>
  );
}

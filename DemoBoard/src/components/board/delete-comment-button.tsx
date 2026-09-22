"use client";

import { useTransition } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { deleteCommentAction } from "@/app/posts/actions";

export function DeleteCommentButton({
  postId,
  commentId,
}: {
  postId: string;
  commentId: string;
}) {
  const [pending, startTransition] = useTransition();

  return (
    <Button
      variant="ghost"
      size="icon-xs"
      aria-label="댓글 삭제"
      disabled={pending}
      onClick={() => startTransition(() => deleteCommentAction(postId, commentId))}
    >
      <X />
    </Button>
  );
}

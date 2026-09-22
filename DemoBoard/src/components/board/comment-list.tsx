import type { Comment } from "@/lib/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DeleteCommentButton } from "@/components/board/delete-comment-button";

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function CommentList({ postId, comments }: { postId: string; comments: Comment[] }) {
  if (comments.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        아직 댓글이 없습니다. 첫 댓글을 남겨보세요.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-4">
      {comments.map((comment) => (
        <li key={comment.id} className="flex items-start gap-3">
          <Avatar className="size-8 shrink-0">
            <AvatarFallback>{comment.author.slice(0, 1)}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{comment.author}</span>
              <span className="text-xs text-muted-foreground">
                {formatDateTime(comment.createdAt)}
              </span>
            </div>
            <p className="mt-0.5 text-sm whitespace-pre-wrap">{comment.content}</p>
          </div>
          <DeleteCommentButton postId={postId} commentId={comment.id} />
        </li>
      ))}
    </ul>
  );
}

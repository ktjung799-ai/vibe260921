import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Eye, Pencil } from "lucide-react";
import { getPost, incrementViews } from "@/lib/posts";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { DeletePostButton } from "@/components/board/delete-post-button";
import { CommentForm } from "@/components/board/comment-form";
import { CommentList } from "@/components/board/comment-list";
import { ToastOnParam } from "@/components/board/toast-on-param";

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function PostDetailPage(props: PageProps<"/posts/[id]">) {
  const { id } = await props.params;
  const post = await getPost(id);

  if (!post) {
    notFound();
  }

  await incrementViews(id);

  return (
    <div className="flex flex-col gap-6">
      <ToastOnParam param="created" message="글이 등록되었습니다." />
      <ToastOnParam param="updated" message="글이 수정되었습니다." />

      <div>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/" />}>
          <ArrowLeft data-icon="inline-start" />
          목록으로
        </Button>
      </div>

      <Card>
        <CardHeader className="gap-2 border-b pb-4">
          <h1 className="font-heading text-xl font-semibold text-balance">{post.title}</h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{post.author}</span>
            <span>{formatDateTime(post.createdAt)}</span>
            {post.updatedAt !== post.createdAt && <span>(수정됨)</span>}
            <span className="ml-auto inline-flex items-center gap-1">
              <Eye className="size-3.5" />
              조회 {post.views}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{post.content}</p>
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={<Link href={`/posts/${post.id}/edit`} />}
          >
            <Pencil data-icon="inline-start" />
            수정
          </Button>
          <DeletePostButton postId={post.id} />
        </CardFooter>
      </Card>

      <div>
        <h2 className="mb-3 font-heading text-base font-medium">
          댓글 <span className="text-muted-foreground">{post.comments.length}</span>
        </h2>
        <CommentList postId={post.id} comments={post.comments} />
        <Separator className="my-4" />
        <CommentForm postId={post.id} />
      </div>
    </div>
  );
}

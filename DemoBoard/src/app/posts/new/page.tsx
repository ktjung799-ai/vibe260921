import { PostForm } from "@/components/board/post-form";
import { createPostAction } from "@/app/posts/actions";

export const metadata = { title: "글쓰기 - DemoBoard" };

export default function NewPostPage() {
  return (
    <PostForm
      title="새 글 작성"
      action={createPostAction}
      submitLabel="등록"
      cancelHref="/"
    />
  );
}

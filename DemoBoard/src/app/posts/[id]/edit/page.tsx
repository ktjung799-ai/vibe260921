import { notFound } from "next/navigation";
import { getPost } from "@/lib/posts";
import { PostForm } from "@/components/board/post-form";
import { updatePostAction } from "@/app/posts/actions";

export default async function EditPostPage(props: PageProps<"/posts/[id]/edit">) {
  const { id } = await props.params;
  const post = await getPost(id);

  if (!post) {
    notFound();
  }

  const action = updatePostAction.bind(null, post.id);

  return (
    <PostForm
      title="글 수정"
      action={action}
      submitLabel="수정 완료"
      cancelHref={`/posts/${post.id}`}
      defaultValues={{ title: post.title, author: post.author, content: post.content }}
    />
  );
}

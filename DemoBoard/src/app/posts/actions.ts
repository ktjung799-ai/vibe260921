"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import * as posts from "@/lib/posts";

export type ActionState = { error?: string } | undefined;

function clean(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function createPostAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const title = clean(formData.get("title"));
  const author = clean(formData.get("author"));
  const content = clean(formData.get("content"));

  if (!title || !author || !content) {
    return { error: "제목, 작성자, 내용을 모두 입력해 주세요." };
  }

  const post = await posts.createPost({ title, author, content });
  revalidatePath("/");
  redirect(`/posts/${post.id}?created=1`);
}

export async function updatePostAction(
  id: string,
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const title = clean(formData.get("title"));
  const author = clean(formData.get("author"));
  const content = clean(formData.get("content"));

  if (!title || !author || !content) {
    return { error: "제목, 작성자, 내용을 모두 입력해 주세요." };
  }

  const updated = await posts.updatePost(id, { title, author, content });
  if (!updated) {
    return { error: "글을 찾을 수 없습니다." };
  }

  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}?updated=1`);
}

export async function deletePostAction(id: string): Promise<void> {
  await posts.deletePost(id);
  revalidatePath("/");
  redirect("/?deleted=1");
}

export async function addCommentAction(
  postId: string,
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const author = clean(formData.get("author"));
  const content = clean(formData.get("content"));

  if (!author || !content) {
    return { error: "작성자와 내용을 입력해 주세요." };
  }

  const comment = await posts.addComment(postId, { author, content });
  if (!comment) {
    return { error: "글을 찾을 수 없습니다." };
  }

  revalidatePath(`/posts/${postId}`);
  return undefined;
}

export async function deleteCommentAction(postId: string, commentId: string): Promise<void> {
  await posts.deleteComment(postId, commentId);
  revalidatePath(`/posts/${postId}`);
}

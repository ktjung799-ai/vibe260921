"use client";

import { useActionState, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { addCommentAction, type ActionState } from "@/app/posts/actions";

export function CommentForm({ postId }: { postId: string }) {
  const action = addCommentAction.bind(null, postId);
  const formRef = useRef<HTMLFormElement>(null);

  async function wrappedAction(prevState: ActionState, formData: FormData) {
    const result = await action(prevState, formData);
    if (!result?.error) {
      formRef.current?.reset();
    }
    return result;
  }

  const [state, formAction, pending] = useActionState<ActionState, FormData>(
    wrappedAction,
    undefined
  );

  return (
    <form ref={formRef} action={formAction} className="flex flex-col gap-3">
      <div className="flex gap-2">
        <Input
          name="author"
          placeholder="이름"
          required
          maxLength={50}
          className="max-w-40"
        />
      </div>
      <Textarea name="content" placeholder="댓글을 입력하세요" required rows={3} />
      {state?.error && (
        <p role="alert" className="text-sm text-destructive">
          {state.error}
        </p>
      )}
      <div className="flex justify-end">
        <Button type="submit" size="sm" disabled={pending}>
          {pending ? "등록 중..." : "댓글 등록"}
        </Button>
      </div>
    </form>
  );
}

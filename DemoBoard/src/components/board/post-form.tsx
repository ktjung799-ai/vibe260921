"use client";

import { useActionState } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import type { ActionState } from "@/app/posts/actions";

export function PostForm({
  title,
  action,
  submitLabel,
  cancelHref,
  defaultValues,
}: {
  title: string;
  action: (prevState: ActionState, formData: FormData) => Promise<ActionState>;
  submitLabel: string;
  cancelHref: string;
  defaultValues?: { title: string; author: string; content: string };
}) {
  const [state, formAction, pending] = useActionState<ActionState, FormData>(
    action,
    undefined
  );

  return (
    <Card>
      <form action={formAction}>
        <CardHeader>
          <CardTitle className="font-heading text-xl">{title}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="title">제목</Label>
            <Input
              id="title"
              name="title"
              required
              maxLength={200}
              defaultValue={defaultValues?.title}
              placeholder="제목을 입력하세요"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="author">작성자</Label>
            <Input
              id="author"
              name="author"
              required
              maxLength={50}
              defaultValue={defaultValues?.author}
              placeholder="이름을 입력하세요"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="content">내용</Label>
            <Textarea
              id="content"
              name="content"
              required
              rows={12}
              defaultValue={defaultValues?.content}
              placeholder="내용을 입력하세요"
            />
          </div>
          {state?.error && (
            <p role="alert" className="text-sm text-destructive">
              {state.error}
            </p>
          )}
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button type="button" variant="outline" nativeButton={false} render={<a href={cancelHref} />}>
            취소
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "저장 중..." : submitLabel}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

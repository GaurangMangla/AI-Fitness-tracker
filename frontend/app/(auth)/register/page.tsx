"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { PrimaryButton } from "@/components/shared/primary-button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { ApiError, apiFetch } from "@/lib/api-client";
import { handleAuthSuccess } from "@/lib/handle-auth-success";
import { type RegisterFormValues, registerSchema } from "@/lib/validators/auth";
import type { AuthResponse } from "@/types/user";

/**
 * Purely informational — shown below the register form so people know
 * what's coming right after they sign up, and why. Not part of the actual
 * onboarding flow itself (that's a separate page, untouched by this file).
 */
const ONBOARDING_PREVIEW_STEPS = [
  "Your body & goals — age, weight, height, and what you're training for",
  "Your experience & equipment — so your plan actually fits what you have",
  "Your schedule — how many days a week you want to train",
];

export default function RegisterPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: RegisterFormValues) =>
      apiFetch<AuthResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: values.email, password: values.password }),
      }),
    onSuccess: (data) => {
      toast.success("Account created. Let's set up your profile.");
      handleAuthSuccess(data, queryClient, router);
    },
    onError: (error: ApiError) => {
      toast.error(error.message);
    },
  });

  return (
    <>
    <Card className="w-full shadow-lg">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Start training smarter today.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="Enter your email" autoComplete="email" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder="At least 8 characters"
                      autoComplete="new-password"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm password</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder="Re-enter your password"
                      autoComplete="new-password"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <PrimaryButton type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating account…" : "Create account"}
            </PrimaryButton>
          </form>
        </Form>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>

    {/* Purely informational — see ONBOARDING_PREVIEW_STEPS above. Not part
        of the actual registration form or its submit logic. */}
    <div className="mt-4 space-y-3 rounded-lg border bg-muted/30 p-4 text-sm">
      <p className="font-medium">Right after this, you&apos;ll tell us:</p>
      <ol className="space-y-1.5 text-muted-foreground">
        {ONBOARDING_PREVIEW_STEPS.map((step, i) => (
          <li key={step} className="flex gap-2">
            <span className="font-medium text-primary">{i + 1}.</span>
            {step}
          </li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        We only ask for this to build your actual workout and nutrition plan —
        never for anything else.
      </p>
    </div>
    </>
  );
}

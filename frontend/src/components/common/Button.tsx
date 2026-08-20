import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  children: ReactNode;
}

export function Button({ loading = false, disabled, children, ...props }: ButtonProps) {
  return (
    <button type="button" disabled={disabled || loading} {...props}>
      {children}
    </button>
  );
}

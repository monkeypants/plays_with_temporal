import * as React from "react";
import { cn } from "@/lib/utils";

type FieldProps = React.HTMLAttributes<HTMLDivElement>;

type FieldSetProps = React.HTMLAttributes<HTMLFieldSetElement>;

type FieldGroupProps = React.HTMLAttributes<HTMLDivElement>;

type FieldDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

type FieldErrorProps = React.HTMLAttributes<HTMLParagraphElement>;

const Field = React.forwardRef<HTMLDivElement, FieldProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("space-y-2", className)} {...props} />
  ),
);
Field.displayName = "Field";

const FieldSet = React.forwardRef<HTMLFieldSetElement, FieldSetProps>(
  ({ className, ...props }, ref) => (
    <fieldset ref={ref} className={cn("space-y-6", className)} {...props} />
  ),
);
FieldSet.displayName = "FieldSet";

const FieldGroup = React.forwardRef<HTMLDivElement, FieldGroupProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("space-y-2", className)} {...props} />
  ),
);
FieldGroup.displayName = "FieldGroup";

const FieldDescription = React.forwardRef<
  HTMLParagraphElement,
  FieldDescriptionProps
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
FieldDescription.displayName = "FieldDescription";

const FieldError = React.forwardRef<HTMLParagraphElement, FieldErrorProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-sm font-medium text-destructive", className)}
      {...props}
    />
  ),
);
FieldError.displayName = "FieldError";

export { Field, FieldSet, FieldGroup, FieldDescription, FieldError };

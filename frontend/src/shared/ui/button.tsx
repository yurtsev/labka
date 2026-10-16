import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Кнопки Material 3: заливка, тональная, контурная, текстовая; у иконок — круглые.
const buttonVariants = cva(
  "group/button relative inline-flex shrink-0 items-center justify-center rounded-full border border-transparent text-sm font-medium tracking-[0.01em] whitespace-nowrap transition-[background-color,box-shadow,color] outline-none select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-40 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-[color-mix(in_srgb,var(--primary),var(--primary-foreground)_8%)] hover:shadow-elevation-1 active:bg-[color-mix(in_srgb,var(--primary),var(--primary-foreground)_12%)]",
        secondary: "bg-nav-active text-on-nav-active hover:bg-[color-mix(in_srgb,var(--nav-active),var(--on-nav-active)_8%)] aria-expanded:bg-[color-mix(in_srgb,var(--nav-active),var(--on-nav-active)_12%)]",
        outline: "border-outline text-primary hover:bg-primary/8 active:bg-primary/12 aria-expanded:bg-primary/12",
        ghost: "text-primary hover:bg-primary/8 active:bg-primary/12 aria-expanded:bg-primary/12",
        destructive: "text-destructive hover:bg-destructive/8 active:bg-destructive/12",
        link: "h-auto! rounded-sm px-0! text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 gap-2 px-6 has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4",
        xs: "h-7 gap-1 px-3 text-xs has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-4",
        sm: "h-8 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3 [&_svg:not([class*='size-'])]:size-[18px]",
        lg: "h-12 gap-2 px-8 text-base has-data-[icon=inline-start]:pl-6",
        icon: "size-10",
        "icon-xs": "size-7 [&_svg:not([class*='size-'])]:size-4",
        "icon-sm": "size-8 [&_svg:not([class*='size-'])]:size-[18px]",
        "icon-lg": "size-12 [&_svg:not([class*='size-'])]:size-6",
      },
    },
    compoundVariants: [
      // Иконки-кнопки без подложки — цвета текста, как в продуктах Google.
      ...(["icon", "icon-xs", "icon-sm", "icon-lg"] as const).map((size) => ({
        variant: "ghost" as const,
        size,
        className: "text-muted-foreground hover:bg-foreground/8 hover:text-foreground active:bg-foreground/12 aria-expanded:bg-foreground/12",
      })),
      ...(["icon", "icon-xs", "icon-sm", "icon-lg"] as const).map((size) => ({
        variant: "outline" as const,
        size,
        className: "border-border text-muted-foreground hover:bg-foreground/8 hover:text-foreground",
      })),
    ],
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }

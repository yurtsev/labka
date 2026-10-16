import * as React from "react"
import { cn } from "cn"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-10 py-2 file:mr-3 file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-primary w-full min-w-0 rounded-[4px] border border-input bg-transparent px-3.5 text-base text-foreground transition-[border-color,box-shadow] outline-none placeholder:text-muted-foreground/80 hover:border-foreground focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-inset disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40 aria-invalid:border-destructive aria-invalid:ring-1 aria-invalid:ring-destructive aria-invalid:ring-inset md:text-sm",
        className
      )}
      {...props}
    />
  )
}

export { Input }

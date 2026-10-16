import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from '@/shared/ui/icons'

const Toaster = ({ ...props }: ToasterProps) => {
  const theme = "dark"

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: (
          <CircleCheckIcon className="size-5" />
        ),
        info: (
          <InfoIcon className="size-5" />
        ),
        warning: (
          <TriangleAlertIcon className="size-5" />
        ),
        error: (
          <OctagonXIcon className="size-5" />
        ),
        loading: (
          <Loader2Icon className="size-5 animate-spin" />
        ),
      }}
      style={
        {
          // Snackbar Google: светлая плашка на тёмном фоне.
          "--normal-bg": "#e3e3e3",
          "--normal-text": "#1f1f1f",
          "--normal-border": "transparent",
          "--border-radius": "4px",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast shadow-elevation-3! font-sans!",
          actionButton: "bg-transparent! text-[#0b57d0]! font-medium! hover:bg-[#0b57d0]/8!",
          description: "text-[#444746]!",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-error-600 text-error-50 hover:bg-error-700",
        outline: "text-foreground",
        success:
          "border-transparent bg-success-600 text-success-50 hover:bg-success-700",
        warning:
          "border-transparent bg-warning-600 text-warning-50 hover:bg-warning-700",
        info:
          "border-transparent bg-primary-600 text-primary-50 hover:bg-primary-700",
        glass:
          "border-white/20 bg-white/10 text-slate-900 backdrop-blur-sm",
        gradient:
          "border-transparent bg-gradient-to-r from-primary-600 to-primary-700 text-white",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.5 text-xs rounded-md",
        lg: "px-3 py-1 text-sm rounded-lg",
        xl: "px-4 py-1.5 text-base rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
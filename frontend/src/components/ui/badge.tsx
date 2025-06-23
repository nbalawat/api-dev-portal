import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-blue-100 text-blue-900 dark:bg-blue-900/20 dark:text-blue-400",
        secondary:
          "border-transparent bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100",
        destructive:
          "border-transparent bg-red-100 text-red-900 dark:bg-red-900/20 dark:text-red-400",
        outline: "text-gray-900 dark:text-gray-100 border-gray-200 dark:border-gray-700 bg-transparent",
        success:
          "border-transparent bg-green-600 text-white dark:bg-green-700 dark:text-white",
        warning:
          "border-transparent bg-amber-100 text-amber-900 dark:bg-amber-900/20 dark:text-amber-400",
        info:
          "border-transparent bg-blue-100 text-blue-900 dark:bg-blue-900/20 dark:text-blue-400",
        glass:
          "border border-gray-200/50 dark:border-gray-700/50 bg-white/80 dark:bg-gray-900/80 text-gray-900 dark:text-gray-100 backdrop-blur-sm",
        gradient:
          "border-transparent bg-gradient-to-r from-blue-600 to-purple-600 text-white",
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
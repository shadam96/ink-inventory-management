import * as React from "react"
import { ChevronUp, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

export interface QuantityInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  /** Shown inside the field so users know what unit the number is in (e.g. the item's unit_of_measure). */
  unit?: string
}

// Native <input type="number"> spin buttons can't be restyled (Firefox
// ignores webkit pseudo-elements entirely), so they're hidden and replaced
// with real buttons here. Value changes go through the browser's own
// input-value setter + a dispatched "input" event so react-hook-form's
// register()-based onChange (which listens at the DOM level) still fires.
// min/max/step stay string|number (like the native attributes, and like
// what react-hook-form's register() spreads in) rather than narrowing to
// number, so they can be spread straight through without a type conflict.
const QuantityInput = React.forwardRef<HTMLInputElement, QuantityInputProps>(
  ({ className, step = 1, min, max, unit, disabled, ...props }, forwardedRef) => {
    const innerRef = React.useRef<HTMLInputElement | null>(null)

    const setRefs = (node: HTMLInputElement | null) => {
      innerRef.current = node
      if (typeof forwardedRef === "function") forwardedRef(node)
      else if (forwardedRef) (forwardedRef as React.MutableRefObject<HTMLInputElement | null>).current = node
    }

    const stepNum = Number(step) || 1
    const minNum = min !== undefined ? Number(min) : undefined
    const maxNum = max !== undefined ? Number(max) : undefined

    const bump = (direction: 1 | -1) => {
      const input = innerRef.current
      if (!input || disabled) return
      const current = parseFloat(input.value)
      const base = Number.isFinite(current) ? current : (minNum ?? 0)
      let next = base + direction * stepNum
      if (minNum !== undefined) next = Math.max(minNum, next)
      if (maxNum !== undefined) next = Math.min(maxNum, next)
      const decimals = (String(stepNum).split(".")[1] || "").length
      next = Math.round(next * 10 ** decimals) / 10 ** decimals

      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set
      setter?.call(input, String(next))
      input.dispatchEvent(new Event("input", { bubbles: true }))
      input.focus()
    }

    return (
      <div
        className={cn(
          // overflow-hidden is a safety net on top of the grid-based button
          // sizing below, so nothing can ever visually escape the rounded
          // border regardless of a particular browser's quirks.
          "flex h-10 w-full items-stretch overflow-hidden rounded-md border border-input bg-background text-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
          disabled && "cursor-not-allowed opacity-50",
          className
        )}
      >
        <input
          ref={setRefs}
          type="number"
          step={step}
          min={min}
          max={max}
          disabled={disabled}
          className="min-w-0 flex-1 rounded-s-md bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          {...props}
        />
        {unit && (
          <span className="flex select-none items-center pe-2 text-xs text-muted-foreground">
            {unit}
          </span>
        )}
        {/* A fixed h-10/h-5 split (and h-1/2 before that) both assumed the
            row resolves to exactly 40px, which some mobile browsers don't
            honor - a UA/accessibility minimum touch-target size on
            <button> can expand the increment button past its intended
            share, and with overflow-hidden that pushes the decrement
            button out of view entirely instead of just poking out below
            the border like before. CSS Grid with grid-rows-2 sidesteps
            this: Tailwind's grid-rows-* utilities use minmax(0, 1fr)
            tracks, which - unlike flex's content-based min-size - cannot
            be forced larger than their equal share by a child's own
            sizing, so both buttons are always exactly half of h-10. */}
        <div className="grid h-10 w-7 grid-rows-2 border-s border-input">
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            onClick={() => bump(1)}
            aria-label="Increment"
            className="flex min-h-0 items-center justify-center rounded-se-md text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none"
          >
            <ChevronUp className="h-3 w-3" />
          </button>
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            onClick={() => bump(-1)}
            aria-label="Decrement"
            className="flex min-h-0 items-center justify-center rounded-ee-md border-t border-input text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none"
          >
            <ChevronDown className="h-3 w-3" />
          </button>
        </div>
      </div>
    )
  }
)
QuantityInput.displayName = "QuantityInput"

export { QuantityInput }

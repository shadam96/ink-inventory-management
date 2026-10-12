import { useState } from 'react'
import { ArrowUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

type SortOrder = 'asc' | 'desc'

export interface SortOption {
  key: string
  label: string
  ascLabel: string
  descLabel: string
}

interface SortSheetProps {
  title: string
  options: SortOption[]
  sortBy: string
  sortOrder: SortOrder
  /** When false, the trigger shows a dot so a changed order is visible while the sheet is closed. */
  isDefaultSort: boolean
  onSort: (key: string, order: SortOrder) => void
  className?: string
}

// Touch counterpart to SortableTableHead: a button that opens a bottom sheet
// with one row per field, each offering both directions as a single tap.
export function SortSheet({
  title,
  options,
  sortBy,
  sortOrder,
  isDefaultSort,
  onSort,
  className,
}: SortSheetProps) {
  const [open, setOpen] = useState(false)

  const select = (key: string, order: SortOrder) => {
    onSort(key, order)
    setOpen(false)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {/* min-h/w-0: index.css raises mobile buttons to 44px, which would
            make this taller than the 40px search field it sits beside */}
        <Button
          variant="outline"
          size="icon"
          aria-label={title}
          className={cn('relative shrink-0 min-h-0 min-w-0', className)}
        >
          <ArrowUpDown className="w-4 h-4" />
          {!isDefaultSort && (
            <span className="absolute top-1.5 end-1.5 w-2 h-2 rounded-full bg-primary" />
          )}
        </Button>
      </SheetTrigger>
      <SheetContent
        side="bottom"
        aria-describedby={undefined}
        className="max-h-[85vh] overflow-y-auto pb-[max(1.5rem,env(safe-area-inset-bottom))]"
      >
        <SheetHeader className="sm:text-center">
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <div className="mt-2 divide-y">
          {options.map((option) => (
            <div
              key={option.key}
              role="group"
              aria-label={option.label}
              className="flex items-center justify-between gap-3 py-3"
            >
              <span className="text-sm font-medium">{option.label}</span>
              {/* Fixed width keeps the toggles aligned down the sheet; a
                  long translation wraps inside its half instead */}
              <div className="grid w-52 shrink-0 grid-cols-2 gap-1 rounded-lg bg-muted p-1">
                {(['asc', 'desc'] as const).map((order) => {
                  const selected = sortBy === option.key && sortOrder === order
                  return (
                    <button
                      key={order}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => select(option.key, order)}
                      className={cn(
                        'rounded-md px-2 py-1.5 text-sm leading-tight transition-colors',
                        selected
                          ? 'bg-primary text-primary-foreground font-medium shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      {order === 'asc' ? option.ascLabel : option.descLabel}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

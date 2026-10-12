import * as React from "react"
import { useTranslation } from "react-i18next"
import { CalendarDays } from "lucide-react"

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { ChevronStart, ChevronEnd } from "@/components/ui/DirectionalIcon"
import { cn } from "@/lib/utils"
import i18n from "@/i18n"
import { resolveLanguage } from "@/i18n/config"

export interface DateFieldProps {
  id?: string
  value?: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
  "aria-invalid"?: boolean
}

// ---- UTC-safe "YYYY-MM-DD" <-> Date helpers ----
// A date-only value must never round-trip through `new Date(isoString)` -
// that parses as UTC midnight, and reading local Y/M/D back off it can
// land on the wrong calendar day for any negative UTC offset. Every
// conversion below goes through local numeric components instead, the
// same discipline daysUntilExpiration already follows in lib/utils.ts.
function parseISODateOnly(value: string | undefined): Date | null {
  if (!value) return null
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

function toISODateOnly(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, "0")
  const d = String(date.getDate()).padStart(2, "0")
  return `${y}-${m}-${d}`
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function addMonths(date: Date, delta: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1)
}

const DAYS_PER_WEEK = 7
const GRID_WEEKS = 6

function buildMonthGrid(monthAnchor: Date): Date[] {
  const first = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), 1)
  const gridStart = new Date(first.getFullYear(), first.getMonth(), 1 - first.getDay())
  return Array.from({ length: DAYS_PER_WEEK * GRID_WEEKS }, (_, i) => {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    return d
  })
}

/**
 * A calendar-dropdown date picker replacing the browser's native
 * `<input type="date">` - gives every platform (desktop, Android, iOS
 * Safari) an identical, styled picker instead of each browser's own
 * inconsistent native widget. `value`/`onChange` use the same
 * "YYYY-MM-DD" string shape the native input produced, so callers don't
 * change their form schema.
 */
export function DateField({
  id,
  value,
  onChange,
  placeholder,
  className,
  disabled,
  ...rest
}: DateFieldProps) {
  const { t } = useTranslation()
  const [open, setOpen] = React.useState(false)
  const selected = parseISODateOnly(value)
  const [viewMonth, setViewMonth] = React.useState<Date>(() => selected ?? new Date())

  // Re-anchor the visible month to the current value every time the
  // popover opens, so re-opening after picking a date (or after the field
  // was set programmatically, e.g. barcode auto-fill) shows that month
  // instead of wherever navigation last left off.
  React.useEffect(() => {
    if (open) setViewMonth(selected ?? new Date())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const locale = resolveLanguage(i18n.language).intlLocale
  const monthLabel = React.useMemo(
    () => new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(viewMonth),
    [locale, viewMonth]
  )
  const weekdayFormatter = React.useMemo(
    () => new Intl.DateTimeFormat(locale, { weekday: "narrow" }),
    [locale]
  )
  const dayFormatter = React.useMemo(
    () => new Intl.DateTimeFormat(locale, { day: "numeric" }),
    [locale]
  )
  const displayFormatter = React.useMemo(
    () => new Intl.DateTimeFormat(locale, { day: "2-digit", month: "2-digit", year: "numeric" }),
    [locale]
  )

  const grid = React.useMemo(() => buildMonthGrid(viewMonth), [viewMonth])
  const weekdayLabels = React.useMemo(
    () => grid.slice(0, DAYS_PER_WEEK).map((d) => weekdayFormatter.format(d)),
    [grid, weekdayFormatter]
  )
  const today = new Date()

  const handleSelect = (day: Date) => {
    onChange(toISODateOnly(day))
    setOpen(false)
  }

  const displayLabel = selected ? displayFormatter.format(selected) : null

  return (
    <Popover open={open} onOpenChange={disabled ? undefined : setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          id={id}
          disabled={disabled}
          className={cn(
            "flex h-10 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          {...rest}
        >
          <span className={cn("truncate", !displayLabel && "text-muted-foreground")}>
            {displayLabel ?? placeholder ?? t("common.selectDate")}
          </span>
          <CalendarDays className="h-4 w-4 shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-3" align="start">
        <div className="flex items-center justify-between mb-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setViewMonth((m) => addMonths(m, -1))}
            aria-label={t("common.previousMonth")}
          >
            <ChevronStart className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium capitalize">{monthLabel}</span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setViewMonth((m) => addMonths(m, 1))}
            aria-label={t("common.nextMonth")}
          >
            <ChevronEnd className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid grid-cols-7 gap-1 mb-1">
          {weekdayLabels.map((label, i) => (
            <div
              key={i}
              className="h-8 flex items-center justify-center text-xs font-medium text-muted-foreground"
            >
              {label}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {grid.map((day, i) => {
            const inMonth = day.getMonth() === viewMonth.getMonth()
            const isToday = isSameDay(day, today)
            const isSelected = selected ? isSameDay(day, selected) : false
            return (
              <button
                key={i}
                type="button"
                onClick={() => handleSelect(day)}
                // h-9/w-9 (36px) keeps every day cell comfortably above the
                // ~40px touch-target guidance on mobile, same intent as the
                // sticky action bars added elsewhere in the mobile-first pass.
                className={cn(
                  "h-9 w-9 rounded-md text-sm transition-colors flex items-center justify-center touch-manipulation",
                  !inMonth && "text-muted-foreground/40",
                  inMonth && !isSelected && "text-foreground hover:bg-accent hover:text-accent-foreground",
                  isToday && !isSelected && "ring-1 ring-inset ring-primary/50",
                  isSelected && "bg-primary text-primary-foreground hover:bg-primary/90"
                )}
              >
                {dayFormatter.format(day)}
              </button>
            )
          })}
        </div>

        <div className="flex items-center justify-between mt-2 pt-2 border-t">
          <Button type="button" variant="ghost" size="sm" onClick={() => handleSelect(new Date())}>
            {t("common.today")}
          </Button>
          {value && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={() => {
                onChange("")
                setOpen(false)
              }}
            >
              {t("common.clear")}
            </Button>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

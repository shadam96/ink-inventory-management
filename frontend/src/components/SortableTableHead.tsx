import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react'
import { TableHead } from '@/components/ui/table'
import { cn } from '@/lib/utils'

interface SortableTableHeadProps {
  children: React.ReactNode
  sortKey: string
  currentSort?: string | null
  currentOrder?: 'asc' | 'desc'
  onSort: (key: string) => void
  className?: string
}

export function SortableTableHead({
  children,
  sortKey,
  currentSort,
  currentOrder = 'asc',
  onSort,
  className,
}: SortableTableHeadProps) {
  const isActive = currentSort === sortKey

  return (
    <TableHead
      className={cn('cursor-pointer select-none hover:bg-accent/50 transition-colors', className)}
      onClick={() => onSort(sortKey)}
    >
      <div className="flex items-center gap-1.5">
        <span>{children}</span>
        {isActive ? (
          currentOrder === 'asc' ? (
            <ArrowUp className="w-3.5 h-3.5 text-primary" />
          ) : (
            <ArrowDown className="w-3.5 h-3.5 text-primary" />
          )
        ) : (
          <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground/40" />
        )}
      </div>
    </TableHead>
  )
}

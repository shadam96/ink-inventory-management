import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Printer, Mail, FileText, Truck } from 'lucide-react'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { pickingApi } from '@/lib/api'
import { openPdfInNewTab } from '@/lib/utils'

type DocumentType = 'pick_note' | 'delivery_note'
type DocumentAction = 'print' | 'email'

interface PostPickDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  referenceNumber: string | null
}

export function PostPickDialog({ open, onOpenChange, referenceNumber }: PostPickDialogProps) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState<`${DocumentType}-${DocumentAction}` | null>(null)

  const handle = async (documentType: DocumentType, action: DocumentAction) => {
    if (!referenceNumber) return
    const key = `${documentType}-${action}` as const
    setBusy(key)
    try {
      const response = await pickingApi.generateDispatchDocument(
        referenceNumber,
        documentType,
        action,
      )
      // Honor the backend's success flag — e.g. a delivery note can't be
      // produced when no customer was selected for this dispatch, or an
      // email can't be sent when the customer has no address on file.
      if (response.success) {
        toast.success(response.message)
        if (action === 'print' && response.pdf_base64) {
          openPdfInNewTab(response.pdf_base64)
        }
      } else {
        toast.info(response.message)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || t('picking.documentError'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t('picking.successDialogTitle')}</DialogTitle>
          <DialogDescription>
            {t('picking.referenceLabel')}:{' '}
            {referenceNumber && (
              <span className="font-mono font-medium" dir="ltr">
                {referenceNumber}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <DocumentSection
            title={t('picking.pickNote')}
            icon={<FileText className="w-4 h-4" />}
            onPrint={() => handle('pick_note', 'print')}
            onEmail={() => handle('pick_note', 'email')}
            printBusy={busy === 'pick_note-print'}
            emailBusy={busy === 'pick_note-email'}
            disabled={busy !== null || !referenceNumber}
          />

          <DocumentSection
            title={t('picking.deliveryNote')}
            icon={<Truck className="w-4 h-4" />}
            onPrint={() => handle('delivery_note', 'print')}
            onEmail={() => handle('delivery_note', 'email')}
            printBusy={busy === 'delivery_note-print'}
            emailBusy={busy === 'delivery_note-email'}
            disabled={busy !== null || !referenceNumber}
          />
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={busy !== null}
          >
            {t('common.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DocumentSection({
  title,
  icon,
  onPrint,
  onEmail,
  printBusy,
  emailBusy,
  disabled,
}: {
  title: string
  icon: React.ReactNode
  onPrint: () => void
  onEmail: () => void
  printBusy: boolean
  emailBusy: boolean
  disabled: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onPrint}
          disabled={disabled}
        >
          {printBusy ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Printer className="w-4 h-4 me-2" />
              {t('common.print')}
            </>
          )}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onEmail}
          disabled={disabled}
        >
          {emailBusy ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Mail className="w-4 h-4 me-2" />
              {t('common.sendEmail')}
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

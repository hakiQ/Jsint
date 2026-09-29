import { createFileRoute, redirect } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDistanceToNow } from 'date-fns'
import { Ban, Check, KeyRound, ShieldCheck, ShieldOff, Trash2, UserPlus } from 'lucide-react'
import { toast } from 'sonner'

import { PageLayout } from '@/components/layout/page-layout'
import FormField from '@/components/shared/form-field'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { useConfirm } from '@/components/use-confirm-dialog'
import { adminService, type UpdateUserPayload } from '@/api/admin-service'
import { adminKeys } from '@/api/query-keys'
import { useAuthStore } from '@/stores/auth-store'
import type { AdminUser } from '@/types/admin'

export const Route = createFileRoute('/_auth/dashboard/admin')({
  beforeLoad: () => {
    // The API enforces this too — this only keeps the page out of the router
    // for non-admins instead of rendering a wall of 403s.
    if (!useAuthStore.getState().user?.is_admin) {
      throw redirect({ to: '/dashboard' })
    }
  },
  component: AdminPage
})

const createUserSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(6, 'At least 6 characters'),
  isAdmin: z.boolean()
})

type CreateUserValues = z.infer<typeof createUserSchema>

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending approval',
  active: 'Active',
  suspended: 'Suspended'
}

const StatusBadge = ({ status }: { status: string }) => (
  <Badge
    variant={status === 'active' ? 'default' : status === 'pending' ? 'outline' : 'destructive'}
    className={status === 'pending' ? 'border-amber-500/50 text-amber-600 dark:text-amber-400' : ''}
  >
    {STATUS_LABEL[status] ?? status}
  </Badge>
)

const NewUserDialog = ({
  open,
  onOpenChange
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) => {
  const queryClient = useQueryClient()
  const methods = useForm<CreateUserValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { email: '', password: '', isAdmin: false }
  })

  const createUser = useMutation({
    mutationFn: (values: CreateUserValues) =>
      adminService.createUser({
        email: values.email,
        password: values.password,
        is_admin: values.isAdmin
      }),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
      toast.success(`Created ${user.email}`)
      methods.reset()
      onOpenChange(false)
    },
    onError: (error: Error) => toast.error(error.message)
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New user</DialogTitle>
          <DialogDescription>
            Accounts created here are approved immediately and can sign in right away.
          </DialogDescription>
        </DialogHeader>

        <FormProvider {...methods}>
          <form
            className="space-y-4"
            onSubmit={methods.handleSubmit((values) => createUser.mutate(values))}
          >
            <FormField name="email" label="Email" type="email" placeholder="analyst@example.com" />
            <FormField
              name="password"
              label="Temporary password"
              type="password"
              placeholder="At least 6 characters"
            />
            <div className="flex items-center justify-between rounded-md border p-3">
              <div className="space-y-0.5">
                <p className="text-sm font-medium">Administrator</p>
                <p className="text-xs text-muted-foreground">
                  Can manage users and approve registrations.
                </p>
              </div>
              <Switch
                checked={methods.watch('isAdmin')}
                onCheckedChange={(checked) => methods.setValue('isAdmin', checked)}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createUser.isPending}>
                {createUser.isPending ? 'Creating…' : 'Create user'}
              </Button>
            </DialogFooter>
          </form>
        </FormProvider>
      </DialogContent>
    </Dialog>
  )
}

const ResetPasswordDialog = ({
  user,
  onClose
}: {
  user: AdminUser | null
  onClose: () => void
}) => {
  const queryClient = useQueryClient()
  const [password, setPassword] = useState('')

  const resetPassword = useMutation({
    mutationFn: () => adminService.updateUser(user!.id, { password }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
      toast.success(`Password updated for ${user?.email}`)
      setPassword('')
      onClose()
    },
    onError: (error: Error) => toast.error(error.message)
  })

  return (
    <Dialog open={!!user} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reset password</DialogTitle>
          <DialogDescription>Set a new password for {user?.email}.</DialogDescription>
        </DialogHeader>
        <Input
          type="password"
          value={password}
          placeholder="New password (min. 6 characters)"
          onChange={(event) => setPassword(event.target.value)}
        />
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={password.length < 6 || resetPassword.isPending}
            onClick={() => resetPassword.mutate()}
          >
            {resetPassword.isPending ? 'Saving…' : 'Save password'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function AdminPage() {
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const { confirm } = useConfirm()
  const [createOpen, setCreateOpen] = useState(false)
  const [resetUser, setResetUser] = useState<AdminUser | null>(null)

  const { data: users = [], isLoading, isError, error } = useQuery({
    queryKey: adminKeys.users,
    queryFn: adminService.listUsers
  })

  const updateUser = useMutation({
    mutationFn: (vars: { id: string; payload: UpdateUserPayload }) =>
      adminService.updateUser(vars.id, vars.payload),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
      toast.success(`Updated ${user.email}`)
    },
    onError: (mutationError: Error) => toast.error(mutationError.message)
  })

  const deleteUser = useMutation({
    mutationFn: (id: string) => adminService.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
      toast.success('User deleted')
    },
    onError: (mutationError: Error) => toast.error(mutationError.message)
  })

  const pending = users.filter((user) => user.status === 'pending')
  const admins = users.filter((user) => user.is_admin)
  const isSelf = (user: AdminUser) => user.id === currentUser?.id

  const handleDelete = async (user: AdminUser) => {
    const ok = await confirm({
      title: 'Delete user',
      message: `Delete ${user.email} and everything they own (${user.investigations} case(s), ${user.sketches} sketch(es))? This cannot be undone.`
    })
    if (ok) deleteUser.mutate(user.id)
  }

  return (
    <PageLayout
      title="Administration"
      description="Approve registrations, manage roles and review what every account owns."
      actions={
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          New user
        </Button>
      }
      isLoading={isLoading}
      error={isError ? (error as Error) : null}
      errorComponent={<p className="text-sm text-destructive">{String(error)}</p>}
      loadingComponent={<p className="text-sm text-muted-foreground">Loading users…</p>}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase text-muted-foreground">Accounts</p>
          <p className="text-2xl font-semibold">{users.length}</p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase text-muted-foreground">Awaiting approval</p>
          <p className="text-2xl font-semibold">{pending.length}</p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase text-muted-foreground">Administrators</p>
          <p className="text-2xl font-semibold">{admins.length}</p>
        </div>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Account</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Cases</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">
                      {user.email}
                      {isSelf(user) && (
                        <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                      )}
                    </span>
                    {(user.first_name || user.last_name) && (
                      <span className="text-xs text-muted-foreground">
                        {[user.first_name, user.last_name].filter(Boolean).join(' ')}
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {user.is_admin ? (
                    <Badge className="gap-1">
                      <ShieldCheck className="h-3 w-3" /> admin
                    </Badge>
                  ) : (
                    <Badge variant="secondary">user</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <StatusBadge status={user.status} />
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {user.investigations}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {user.sketches} sketches · {user.analyses} analyses
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {user.created_at
                    ? formatDistanceToNow(new Date(user.created_at), { addSuffix: true })
                    : '—'}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-1">
                    {user.status === 'pending' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          updateUser.mutate({ id: user.id, payload: { status: 'active' } })
                        }
                      >
                        <Check className="mr-1 h-3.5 w-3.5" />
                        Approve
                      </Button>
                    )}
                    {user.status === 'active' && !isSelf(user) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Suspend account"
                        onClick={() =>
                          updateUser.mutate({ id: user.id, payload: { status: 'suspended' } })
                        }
                      >
                        <Ban className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {user.status === 'suspended' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Reactivate account"
                        onClick={() =>
                          updateUser.mutate({ id: user.id, payload: { status: 'active' } })
                        }
                      >
                        <Check className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {!isSelf(user) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        title={user.is_admin ? 'Remove admin rights' : 'Make administrator'}
                        onClick={() =>
                          updateUser.mutate({
                            id: user.id,
                            payload: { is_admin: !user.is_admin }
                          })
                        }
                      >
                        {user.is_admin ? (
                          <ShieldOff className="h-3.5 w-3.5" />
                        ) : (
                          <ShieldCheck className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      title="Reset password"
                      onClick={() => setResetUser(user)}
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                    </Button>
                    {!isSelf(user) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Delete account"
                        onClick={() => handleDelete(user)}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {users.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  No accounts yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <NewUserDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ResetPasswordDialog user={resetUser} onClose={() => setResetUser(null)} />
    </PageLayout>
  )
}

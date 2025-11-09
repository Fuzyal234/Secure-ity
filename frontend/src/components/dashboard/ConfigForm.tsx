import { useState } from 'react'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, Save, Lock, ShieldCheck, Sparkles, ClipboardCheck } from 'lucide-react'

interface ConfigFormProps {
  onSuccess: () => void
  onCancel: () => void
}

export default function ConfigForm({ onSuccess, onCancel }: ConfigFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [data, setData] = useState('')
  const [loading, setLoading] = useState(false)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const { toast } = useToast()

  const validateJson = (value: string): boolean => {
    if (!value.trim()) {
      setJsonError('Configuration data is required')
      return false
    }
    try {
      JSON.parse(value)
      setJsonError(null)
      return true
    } catch (error) {
      setJsonError('Invalid JSON format')
      return false
    }
  }

  const handleDataChange = (value: string) => {
    setData(value)
    validateJson(value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateJson(data)) {
      return
    }

    setLoading(true)
    try {
      const parsedData = JSON.parse(data)
      await api.createConfig(name, description || null, parsedData)
      onSuccess()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to create configuration',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <Button
        variant="ghost"
        onClick={onCancel}
        className="w-fit rounded-full border border-primary/20 bg-primary/5 px-4"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to configurations
      </Button>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <Card className="border-primary/20 bg-white/85 shadow-lg backdrop-blur">
          <CardHeader className="space-y-4 border-b border-slate-200/60 bg-white/60">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-primary">
              <Lock className="h-4 w-4" />
              New secret
            </div>
            <div className="space-y-1.5">
              <CardTitle className="text-2xl text-slate-900">
                Create a new configuration bundle
              </CardTitle>
              <CardDescription className="text-base text-slate-600">
                Define the context, describe its purpose, and drop in JSON payloads that we&apos;ll encrypt at the edge.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Configuration name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Production database, Payments API keys"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="Give auditors and collaborators a short description of this secret set."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="data">Configuration data (JSON) *</Label>
                <Textarea
                  id="data"
                  placeholder='{"key": "value", "secret": "sensitive_data"}'
                  value={data}
                  onChange={(e) => handleDataChange(e.target.value)}
                  required
                  disabled={loading}
                  rows={12}
                  className="font-mono text-sm"
                />
                {jsonError ? (
                  <p className="text-sm font-medium text-destructive">{jsonError}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    We validate JSON before encrypting with AES-256-GCM. Paste raw objects or arrays—no extra wrapping required.
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onCancel}
                  disabled={loading}
                  className="sm:min-w-[140px]"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={loading || !!jsonError}
                  className="sm:min-w-[200px]"
                >
                  {loading ? (
                    'Saving...'
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save configuration
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="relative overflow-hidden border border-dashed border-primary/30 bg-primary/5 shadow-none">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
            <CardHeader className="relative space-y-3">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-primary" />
                <CardTitle className="text-lg text-slate-900">Hardening checklist</CardTitle>
              </div>
              <CardDescription className="text-sm text-slate-600">
                Follow these guardrails to keep your secrets compliant and audit-ready.
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <div className="flex items-start gap-3 rounded-xl border border-white/40 bg-white/70 p-4 backdrop-blur">
                <Sparkles className="mt-1 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Least privilege labels</p>
                  <p className="text-xs text-slate-600">
                    Use descriptive names and descriptions so RBAC policies can target the right bundles.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-xl border border-white/40 bg-white/70 p-4 backdrop-blur">
                <ClipboardCheck className="mt-1 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">JSON linting</p>
                  <p className="text-xs text-slate-600">
                    We&apos;ll block invalid JSON, but you can also paste from your formatter to maintain schema fidelity.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-xl border border-white/40 bg-white/70 p-4 backdrop-blur">
                <Lock className="mt-1 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Client-side encryption</p>
                  <p className="text-xs text-slate-600">
                    Data is encrypted locally with a rotating key before hitting our API. Review key rotation in KMS settings.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}


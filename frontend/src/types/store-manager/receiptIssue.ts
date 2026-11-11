export type IssueKind = 'Missing' | 'Damaged'

export interface IssueDraft {
  kind: IssueKind
  received: string
  affected: string
  description: string
}

export type IssueErrors = Partial<Record<'received' | 'affected' | 'description', string>>

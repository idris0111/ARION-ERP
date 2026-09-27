export type Entity = Record<string, unknown> & { id: number }
export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] }
export type User = { id: number; username: string; first_name?: string; last_name?: string; email?: string; role: string; is_superuser?: boolean }
export type Organization = Entity & { name: string; currency?: string }
export type Field = { key: string; label: string; type?: 'text'|'number'|'money'|'date'|'datetime'|'textarea'|'select'|'boolean'; required?: boolean; endpoint?: string; options?: { value: string; label: string }[]; placeholder?: string; half?: boolean }
export type Column = { key: string; label: string; type?: 'text'|'money'|'number'|'date'|'datetime'|'status'|'boolean'; link?: boolean }
export type Resource = { key: string; title: string; subtitle: string; endpoint: string; icon: string; columns: Column[]; fields?: Field[]; search?: string[]; create?: boolean; edit?: boolean; remove?: boolean; exportPath?: string; tabs?: { label: string; key: string }[]; permission?: 'sales'|'purchases'|'warehouse'|'finance'|'hr'|'admin'; fixedFilter?: Record<string,string> }

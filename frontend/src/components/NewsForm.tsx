import { useState } from 'react'
import './NewsForm.css'

interface NewsFormProps {
  onSubmit: (title: string, body: string, source: string) => Promise<void>
  isSubmitting: boolean
}

const MIN_LENGTH = 200
const MAX_LENGTH = 10000
const MAX_TITLE_LENGTH = 200
const MAX_SOURCE_LENGTH = 100

export default function NewsForm({ onSubmit, isSubmitting }: NewsFormProps) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [source, setSource] = useState('')
  const [error, setError] = useState<string | null>(null)

  const bodyLength = body.length
  const isValid = bodyLength >= MIN_LENGTH && bodyLength <= MAX_LENGTH

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!isValid) {
      setError(`El cuerpo debe tener entre ${MIN_LENGTH} y ${MAX_LENGTH} caracteres`)
      return
    }

    try {
      await onSubmit(title, body, source)
      // Limpiar formulario después de éxito
      setTitle('')
      setBody('')
      setSource('')
    } catch (err: any) {
      setError(err.message || 'Error al guardar la noticia')
    }
  }

  return (
    <div className="news-form-container">
      <h2>📝 Ingresar Noticia</h2>
      <form onSubmit={handleSubmit} className="news-form">
        <div className="form-group">
          <label htmlFor="title">Título (opcional)</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={MAX_TITLE_LENGTH}
            placeholder="Título de la noticia"
            disabled={isSubmitting}
          />
          <div className="char-count">{title.length} / {MAX_TITLE_LENGTH}</div>
        </div>

        <div className="form-group">
          <label htmlFor="body">
            Cuerpo de la noticia <span className="required">*</span>
          </label>
          <textarea
            id="body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            minLength={MIN_LENGTH}
            maxLength={MAX_LENGTH}
            placeholder="Pega aquí el texto completo de la noticia (mínimo 200 caracteres)"
            disabled={isSubmitting}
            rows={10}
            className={!isValid && bodyLength > 0 ? 'error' : ''}
          />
          <div className={`char-count ${!isValid && bodyLength > 0 ? 'error' : ''}`}>
            {bodyLength} / {MAX_LENGTH} 
            {bodyLength < MIN_LENGTH && bodyLength > 0 && (
              <span className="min-required"> (mínimo {MIN_LENGTH})</span>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="source">Fuente (opcional)</label>
          <input
            id="source"
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            maxLength={MAX_SOURCE_LENGTH}
            placeholder="Ej: El País, BBC News, etc."
            disabled={isSubmitting}
          />
          <div className="char-count">{source.length} / {MAX_SOURCE_LENGTH}</div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          className="submit-button"
        >
          {isSubmitting ? '⏳ Guardando...' : '💾 Guardar Noticia'}
        </button>
      </form>
    </div>
  )
}


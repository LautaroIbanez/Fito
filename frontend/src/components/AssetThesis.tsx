import { useState, useEffect } from 'react'
import { thesisApi, AssetThesis, AssetThesisCreate, ChecklistItem, ChecklistItemCreate, NewsLink, NewsLinkCreate } from '../services/api'
import { portfolioApi, PortfolioItem } from '../services/api'
import { newsApi, NewsItem } from '../services/api'
import './AssetThesis.css'

interface AssetThesisProps {
  portfolioItemId?: number
  onUpdate?: () => void
}

export default function AssetThesisComponent({ portfolioItemId, onUpdate }: AssetThesisProps) {
  const [thesis, setThesis] = useState<AssetThesis | null>(null)
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([])
  const [availableNews, setAvailableNews] = useState<NewsItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [showLinkNews, setShowLinkNews] = useState(false)
  const [showAddChecklist, setShowAddChecklist] = useState(false)
  const [selectedNewsId, setSelectedNewsId] = useState<number | null>(null)
  
  const [formData, setFormData] = useState<AssetThesisCreate>({
    portfolio_item_id: portfolioItemId || 0,
    thesis_text: '',
    entry_reason: '',
    target_price: '',
    stop_loss: '',
    time_horizon: ''
  })
  
  const [newChecklistItem, setNewChecklistItem] = useState<ChecklistItemCreate>({
    title: '',
    description: '',
    order_index: 0
  })

  useEffect(() => {
    loadPortfolioItems()
    loadAvailableNews()
  }, [])

  useEffect(() => {
    if (portfolioItemId) {
      loadThesis(portfolioItemId)
      setFormData({ ...formData, portfolio_item_id: portfolioItemId })
    } else if (portfolioItems.length > 0 && formData.portfolio_item_id === 0) {
      setFormData({ ...formData, portfolio_item_id: portfolioItems[0].id })
    }
  }, [portfolioItemId, portfolioItems])

  const loadPortfolioItems = async () => {
    try {
      const items = await portfolioApi.list()
      setPortfolioItems(items)
      if (!portfolioItemId && items.length > 0) {
        setFormData({ ...formData, portfolio_item_id: items[0].id })
      }
    } catch (err: any) {
      console.error('Error loading portfolio items:', err)
    }
  }

  const loadAvailableNews = async () => {
    try {
      const news = await newsApi.list('date')
      setAvailableNews(news)
    } catch (err: any) {
      console.error('Error loading news:', err)
    }
  }

  const loadThesis = async (itemId: number) => {
    try {
      setIsLoading(true)
      setError(null)
      const theses = await thesisApi.list(itemId)
      if (theses.length > 0) {
        setThesis(theses[0])
        setFormData({
          portfolio_item_id: theses[0].portfolio_item_id,
          thesis_text: theses[0].thesis_text,
          entry_reason: theses[0].entry_reason || '',
          target_price: theses[0].target_price || '',
          stop_loss: theses[0].stop_loss || '',
          time_horizon: theses[0].time_horizon || ''
        })
      } else {
        setThesis(null)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar tesis')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      if (thesis) {
        await thesisApi.update(thesis.id, formData)
      } else {
        const newThesis = await thesisApi.create(formData)
        setThesis(newThesis)
      }
      
      setEditing(false)
      if (formData.portfolio_item_id) {
        await loadThesis(formData.portfolio_item_id)
      }
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar tesis')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLinkNews = async () => {
    if (!thesis || !selectedNewsId) return
    
    try {
      setIsLoading(true)
      setError(null)
      const link: NewsLinkCreate = {
        news_item_id: selectedNewsId,
        is_key_news: true,
        relevance_note: ''
      }
      await thesisApi.linkNews(thesis.id, link)
      await loadThesis(thesis.portfolio_item_id)
      setShowLinkNews(false)
      setSelectedNewsId(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al vincular noticia')
    } finally {
      setIsLoading(false)
    }
  }

  const handleUnlinkNews = async (linkId: number) => {
    if (!thesis) return
    
    try {
      setIsLoading(true)
      await thesisApi.unlinkNews(thesis.id, linkId)
      await loadThesis(thesis.portfolio_item_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al desvincular noticia')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddChecklistItem = async () => {
    if (!thesis) return
    
    try {
      setIsLoading(true)
      setError(null)
      const maxOrder = thesis.checklist_items.length > 0 
        ? Math.max(...thesis.checklist_items.map(i => i.order_index)) + 1 
        : 0
      await thesisApi.createChecklistItem(thesis.id, {
        ...newChecklistItem,
        order_index: maxOrder
      })
      await loadThesis(thesis.portfolio_item_id)
      setNewChecklistItem({ title: '', description: '', order_index: 0 })
      setShowAddChecklist(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al crear item de checklist')
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleChecklistItem = async (item: ChecklistItem) => {
    if (!thesis) return
    
    try {
      await thesisApi.updateChecklistItem(item.id, {
        is_completed: !item.is_completed,
        completed_notes: item.completed_notes
      })
      await loadThesis(thesis.portfolio_item_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al actualizar item')
    }
  }

  const handleDeleteChecklistItem = async (itemId: number) => {
    if (!thesis) return
    
    try {
      await thesisApi.deleteChecklistItem(itemId)
      await loadThesis(thesis.portfolio_item_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar item')
    }
  }

  const handleDeleteThesis = async () => {
    if (!thesis || !confirm('¿Estás seguro de eliminar esta tesis?')) return
    
    try {
      setIsLoading(true)
      await thesisApi.delete(thesis.id)
      setThesis(null)
      setFormData({
        portfolio_item_id: portfolioItemId || 0,
        thesis_text: '',
        entry_reason: '',
        target_price: '',
        stop_loss: '',
        time_horizon: ''
      })
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar tesis')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading && !thesis) {
    return (
      <div className="asset-thesis-container">
        <h2>📝 Tesis de Inversión</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="asset-thesis-container">
      <div className="thesis-header">
        <h2>📝 Tesis de Inversión</h2>
        {thesis && !editing && (
          <button className="edit-button" onClick={() => setEditing(true)}>
            ✏️ Editar
          </button>
        )}
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {!thesis && !editing ? (
        <div className="empty-state">
          <p>No hay tesis registrada para este activo.</p>
          {portfolioItems.length > 0 && (
            <button className="create-button" onClick={() => setEditing(true)}>
              ➕ Crear Tesis
            </button>
          )}
          {portfolioItems.length === 0 && (
            <p className="hint">Primero agrega un activo a tu cartera para crear una tesis.</p>
          )}
        </div>
      ) : (
        <>
          {editing ? (
            <div className="thesis-form">
              {!portfolioItemId && (
                <div className="form-group">
                  <label>Activo *</label>
                  <select
                    value={formData.portfolio_item_id}
                    onChange={(e) => {
                      const newItemId = parseInt(e.target.value)
                      setFormData({ ...formData, portfolio_item_id: newItemId })
                      loadThesis(newItemId)
                    }}
                  >
                    <option value="0">Seleccionar activo...</option>
                    {portfolioItems.map(item => (
                      <option key={item.id} value={item.id}>
                        {item.symbol ? `${item.symbol} - ` : ''}{item.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-group">
                <label>Tesis de Inversión *</label>
                <textarea
                  value={formData.thesis_text}
                  onChange={(e) => setFormData({ ...formData, thesis_text: e.target.value })}
                  placeholder="Describe por qué posees este activo, tu análisis y expectativas..."
                  rows={6}
                />
                <div className="char-count">{formData.thesis_text.length}/5000</div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Razón de Entrada</label>
                  <input
                    type="text"
                    value={formData.entry_reason}
                    onChange={(e) => setFormData({ ...formData, entry_reason: e.target.value })}
                    placeholder="Ej: Breakout técnico"
                  />
                </div>

                <div className="form-group">
                  <label>Precio Objetivo</label>
                  <input
                    type="text"
                    value={formData.target_price}
                    onChange={(e) => setFormData({ ...formData, target_price: e.target.value })}
                    placeholder="Ej: $150"
                  />
                </div>

                <div className="form-group">
                  <label>Stop Loss</label>
                  <input
                    type="text"
                    value={formData.stop_loss}
                    onChange={(e) => setFormData({ ...formData, stop_loss: e.target.value })}
                    placeholder="Ej: $120"
                  />
                </div>

                <div className="form-group">
                  <label>Horizonte Temporal</label>
                  <input
                    type="text"
                    value={formData.time_horizon}
                    onChange={(e) => setFormData({ ...formData, time_horizon: e.target.value })}
                    placeholder="Ej: 6 meses"
                  />
                </div>
              </div>

              <div className="form-actions">
                <button className="save-button" onClick={handleSave} disabled={!formData.thesis_text || formData.thesis_text.length < 50}>
                  💾 Guardar
                </button>
                <button className="cancel-button" onClick={() => {
                  setEditing(false)
                  if (thesis) {
                    setFormData({
                      portfolio_item_id: thesis.portfolio_item_id,
                      thesis_text: thesis.thesis_text,
                      entry_reason: thesis.entry_reason || '',
                      target_price: thesis.target_price || '',
                      stop_loss: thesis.stop_loss || '',
                      time_horizon: thesis.time_horizon || ''
                    })
                  }
                }}>
                  ✕ Cancelar
                </button>
                {thesis && (
                  <button className="delete-button" onClick={handleDeleteThesis}>
                    🗑️ Eliminar Tesis
                  </button>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="thesis-view">
                <div className="thesis-asset-info">
                  <h3>
                    {thesis.portfolio_item_symbol && (
                      <span className="symbol">{thesis.portfolio_item_symbol}</span>
                    )}
                    {thesis.portfolio_item_name || 'Activo'}
                  </h3>
                </div>

                <div className="thesis-content">
                  <h4>Tesis de Inversión</h4>
                  <p className="thesis-text">{thesis.thesis_text}</p>
                </div>

                {(thesis.entry_reason || thesis.target_price || thesis.stop_loss || thesis.time_horizon) && (
                  <div className="thesis-details">
                    {thesis.entry_reason && (
                      <div className="detail-item">
                        <span className="detail-label">Razón de Entrada:</span>
                        <span className="detail-value">{thesis.entry_reason}</span>
                      </div>
                    )}
                    {thesis.target_price && (
                      <div className="detail-item">
                        <span className="detail-label">Precio Objetivo:</span>
                        <span className="detail-value">{thesis.target_price}</span>
                      </div>
                    )}
                    {thesis.stop_loss && (
                      <div className="detail-item">
                        <span className="detail-label">Stop Loss:</span>
                        <span className="detail-value">{thesis.stop_loss}</span>
                      </div>
                    )}
                    {thesis.time_horizon && (
                      <div className="detail-item">
                        <span className="detail-label">Horizonte:</span>
                        <span className="detail-value">{thesis.time_horizon}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="thesis-section">
                  <div className="section-header">
                    <h4>📰 Noticias Clave Vinculadas</h4>
                    <button className="link-button" onClick={() => setShowLinkNews(true)}>
                      ➕ Vincular Noticia
                    </button>
                  </div>

                  {showLinkNews && (
                    <div className="link-news-form">
                      <select
                        value={selectedNewsId || ''}
                        onChange={(e) => setSelectedNewsId(parseInt(e.target.value) || null)}
                      >
                        <option value="">Seleccionar noticia...</option>
                        {availableNews
                          .filter(n => !thesis.linked_news.some(ln => ln.news_item_id === n.id))
                          .map(news => (
                            <option key={news.id} value={news.id}>
                              {news.title || `Noticia #${news.id}`} - {new Date(news.created_at).toLocaleDateString()}
                            </option>
                          ))}
                      </select>
                      <div className="form-actions">
                        <button className="save-button" onClick={handleLinkNews} disabled={!selectedNewsId}>
                          Vincular
                        </button>
                        <button className="cancel-button" onClick={() => {
                          setShowLinkNews(false)
                          setSelectedNewsId(null)
                        }}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}

                  {thesis.linked_news.length === 0 ? (
                    <p className="empty-message">No hay noticias vinculadas.</p>
                  ) : (
                    <div className="linked-news-list">
                      {thesis.linked_news.map(link => (
                        <div key={link.id} className="linked-news-item">
                          <div className="news-link-header">
                            <span className="news-title">{link.news_title || `Noticia #${link.news_item_id}`}</span>
                            {link.is_key_news && <span className="key-badge">⭐ Clave</span>}
                            <button
                              className="unlink-button"
                              onClick={() => handleUnlinkNews(link.id)}
                              title="Desvincular"
                            >
                              ✕
                            </button>
                          </div>
                          {link.relevance_note && (
                            <p className="relevance-note">{link.relevance_note}</p>
                          )}
                          {link.news_body_preview && (
                            <p className="news-preview">{link.news_body_preview}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="thesis-section">
                  <div className="section-header">
                    <h4>✅ Checklist Post-Noticia</h4>
                    <button className="link-button" onClick={() => setShowAddChecklist(true)}>
                      ➕ Agregar Paso
                    </button>
                  </div>

                  {showAddChecklist && (
                    <div className="add-checklist-form">
                      <div className="form-group">
                        <label>Título del Paso *</label>
                        <input
                          type="text"
                          value={newChecklistItem.title}
                          onChange={(e) => setNewChecklistItem({ ...newChecklistItem, title: e.target.value })}
                          placeholder="Ej: Revisar guía de trading"
                        />
                      </div>
                      <div className="form-group">
                        <label>Descripción</label>
                        <textarea
                          value={newChecklistItem.description}
                          onChange={(e) => setNewChecklistItem({ ...newChecklistItem, description: e.target.value })}
                          placeholder="Descripción detallada del paso..."
                          rows={3}
                        />
                      </div>
                      <div className="form-actions">
                        <button className="save-button" onClick={handleAddChecklistItem} disabled={!newChecklistItem.title}>
                          Agregar
                        </button>
                        <button className="cancel-button" onClick={() => {
                          setShowAddChecklist(false)
                          setNewChecklistItem({ title: '', description: '', order_index: 0 })
                        }}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}

                  {thesis.checklist_items.length === 0 ? (
                    <p className="empty-message">No hay items en el checklist. Agrega pasos para seguir después de noticias relevantes.</p>
                  ) : (
                    <div className="checklist-items">
                      {thesis.checklist_items.map(item => (
                        <div key={item.id} className={`checklist-item ${item.is_completed ? 'completed' : ''}`}>
                          <div className="checklist-item-header">
                            <input
                              type="checkbox"
                              checked={item.is_completed}
                              onChange={() => handleToggleChecklistItem(item)}
                              className="checklist-checkbox"
                            />
                            <div className="checklist-item-content">
                              <h5 className={item.is_completed ? 'strikethrough' : ''}>{item.title}</h5>
                              {item.description && (
                                <p className={item.is_completed ? 'strikethrough' : ''}>{item.description}</p>
                              )}
                              {item.is_completed && item.completed_at && (
                                <span className="completed-date">
                                  Completado: {new Date(item.completed_at).toLocaleString()}
                                </span>
                              )}
                            </div>
                            <button
                              className="delete-item-button"
                              onClick={() => handleDeleteChecklistItem(item.id)}
                              title="Eliminar paso"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}


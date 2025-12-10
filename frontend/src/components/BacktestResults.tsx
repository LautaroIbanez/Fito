import { useState, useEffect, useRef } from 'react'
import { BacktestResult } from '../services/api'
import './BacktestResults.css'

interface BacktestResultsProps {
  results: BacktestResult[]
  ruleId: number
}

export default function BacktestResults({ results, ruleId }: BacktestResultsProps) {
  const [selectedResult, setSelectedResult] = useState<BacktestResult | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (results.length > 0 && !selectedResult) {
      setSelectedResult(results[0])
    } else if (selectedResult) {
      const updated = results.find(r => r.id === selectedResult.id)
      if (updated) setSelectedResult(updated)
    }
  }, [results])

  useEffect(() => {
    if (selectedResult && canvasRef.current && selectedResult.equity_curve.length > 0) {
      drawEquityCurve(selectedResult)
    }
  }, [selectedResult])

  const drawEquityCurve = (result: BacktestResult) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = 40
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    // Background
    ctx.fillStyle = '#f8f9fa'
    ctx.fillRect(0, 0, width, height)

    if (result.equity_curve.length === 0) return

    // Find min/max equity for scaling
    const equities = result.equity_curve.map(p => p.equity)
    const minEquity = Math.min(...equities)
    const maxEquity = Math.max(...equities)
    const equityRange = maxEquity - minEquity || 1

    // Draw grid
    ctx.strokeStyle = '#e0e0e0'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }

    // Draw equity curve
    ctx.strokeStyle = '#667eea'
    ctx.lineWidth = 2
    ctx.beginPath()

    result.equity_curve.forEach((point, index) => {
      const x = padding + (chartWidth / (result.equity_curve.length - 1)) * index
      const normalizedEquity = (point.equity - minEquity) / equityRange
      const y = padding + chartHeight - (normalizedEquity * chartHeight)

      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })

    ctx.stroke()

    // Draw points
    ctx.fillStyle = '#667eea'
    result.equity_curve.forEach((point, index) => {
      const x = padding + (chartWidth / (result.equity_curve.length - 1)) * index
      const normalizedEquity = (point.equity - minEquity) / equityRange
      const y = padding + chartHeight - (normalizedEquity * chartHeight)

      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    })

    // Draw labels
    ctx.fillStyle = '#333'
    ctx.font = '12px Arial'
    ctx.textAlign = 'center'

    // Y-axis labels
    for (let i = 0; i <= 5; i++) {
      const value = minEquity + (equityRange / 5) * (5 - i)
      const y = padding + (chartHeight / 5) * i
      ctx.fillText(`$${value.toFixed(0)}`, padding - 10, y + 4)
    }

    // Title
    ctx.font = 'bold 14px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('Equity Curve', width / 2, 20)

    // X-axis label
    ctx.font = '12px Arial'
    ctx.fillText('Trades', width / 2, height - 10)
  }

  if (results.length === 0) {
    return (
      <div className="backtest-results-empty">
        <p>No hay resultados de backtest aún.</p>
        <p className="hint">Ejecuta un backtest para ver los resultados.</p>
      </div>
    )
  }

  return (
    <div className="backtest-results-container">
      <div className="results-selector">
        <label>Resultado a Visualizar:</label>
        <select
          value={selectedResult?.id || ''}
          onChange={(e) => {
            const result = results.find(r => r.id === parseInt(e.target.value))
            if (result) setSelectedResult(result)
          }}
        >
          {results.map((result) => (
            <option key={result.id} value={result.id}>
              {result.rule_name || `Backtest #${result.id}`} - {new Date(result.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>
      </div>

      {selectedResult && (
        <>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Total PnL</div>
              <div className={`metric-value ${selectedResult.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                ${selectedResult.total_pnl.toFixed(2)} ({selectedResult.total_pnl_pct.toFixed(2)}%)
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Win Rate</div>
              <div className="metric-value">{selectedResult.win_rate.toFixed(2)}%</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Total Trades</div>
              <div className="metric-value">{selectedResult.total_trades}</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Ganadores</div>
              <div className="metric-value positive">{selectedResult.winning_trades}</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Perdedores</div>
              <div className="metric-value negative">{selectedResult.losing_trades}</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Avg Win</div>
              <div className="metric-value positive">${selectedResult.average_win.toFixed(2)}</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Avg Loss</div>
              <div className="metric-value negative">${selectedResult.average_loss.toFixed(2)}</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Max Drawdown</div>
              <div className="metric-value negative">
                ${selectedResult.max_drawdown.toFixed(2)} ({selectedResult.max_drawdown_pct.toFixed(2)}%)
              </div>
            </div>
          </div>

          <div className="equity-curve-container">
            <h4>Equity Curve</h4>
            <canvas
              ref={canvasRef}
              width={800}
              height={400}
              className="equity-curve-canvas"
            />
          </div>

          {selectedResult.executed_start_date && selectedResult.executed_end_date && (
            <div className="backtest-period">
              <strong>Período:</strong> {new Date(selectedResult.executed_start_date).toLocaleDateString()} - {new Date(selectedResult.executed_end_date).toLocaleDateString()}
            </div>
          )}
        </>
      )}
    </div>
  )
}



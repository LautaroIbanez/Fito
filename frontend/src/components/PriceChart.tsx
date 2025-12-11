import { useRef, useEffect, useState } from 'react'
import './PriceChart.css'

interface PriceDataPoint {
  date: string | Date
  price: number
}

interface PriceChartProps {
  data: PriceDataPoint[]
  title?: string
  symbol?: string
  height?: number
}

export default function PriceChart({ data, title, symbol, height = 300 }: PriceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [showLegend, setShowLegend] = useState(true)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  // Calcular SMA (Simple Moving Average)
  const calculateSMA = (prices: number[], period: number): number[] => {
    const sma: number[] = []
    for (let i = 0; i < prices.length; i++) {
      if (i < period - 1) {
        sma.push(NaN) // No hay suficientes datos
      } else {
        const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
        sma.push(sum / period)
      }
    }
    return sma
  }

  // Calcular EMA (Exponential Moving Average)
  const calculateEMA = (prices: number[], period: number): number[] => {
    const ema: number[] = []
    const multiplier = 2 / (period + 1)
    
    for (let i = 0; i < prices.length; i++) {
      if (i === 0) {
        ema.push(prices[i]) // Primer valor es el precio mismo
      } else if (i < period - 1) {
        // Para los primeros period-1 valores, usar promedio simple
        const sum = prices.slice(0, i + 1).reduce((a, b) => a + b, 0)
        ema.push(sum / (i + 1))
      } else {
        // EMA = (Precio - EMA anterior) * multiplicador + EMA anterior
        ema.push((prices[i] - ema[i - 1]) * multiplier + ema[i - 1])
      }
    }
    return ema
  }

  useEffect(() => {
    if (!canvasRef.current || data.length === 0) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Ajustar tamaño del canvas
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio
    canvas.height = height * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    const width = rect.width
    const chartHeight = height - 80 // Dejar espacio para labels y leyenda
    const padding = { top: 20, right: 20, bottom: 50, left: 60 }

    // Limpiar canvas
    ctx.clearRect(0, 0, width, height)

    // Fondo
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)

    // Extraer precios
    const prices = data.map(d => d.price)
    const dates = data.map(d => typeof d.date === 'string' ? new Date(d.date) : d.date)

    // Calcular medias móviles
    const ema20 = calculateEMA(prices, 20)
    const sma50 = calculateSMA(prices, 50)

    // Encontrar min/max para escalado
    const allValues = [...prices, ...ema20.filter(v => !isNaN(v)), ...sma50.filter(v => !isNaN(v))]
    const minPrice = Math.min(...allValues)
    const maxPrice = Math.max(...allValues)
    const priceRange = maxPrice - minPrice || 1

    // Dibujar grid
    ctx.strokeStyle = '#e0e0e0'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()
    }

    // Función para convertir precio a coordenada Y
    const priceToY = (price: number) => {
      const normalized = (price - minPrice) / priceRange
      return padding.top + chartHeight - (normalized * chartHeight)
    }

    // Función para convertir índice a coordenada X
    const indexToX = (index: number) => {
      return padding.left + ((width - padding.left - padding.right) / (data.length - 1)) * index
    }

    // Dibujar SMA 50 (línea más gruesa, color azul)
    ctx.strokeStyle = '#4A90E2'
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.beginPath()
    let smaPathStarted = false
    sma50.forEach((value, index) => {
      if (!isNaN(value)) {
        const x = indexToX(index)
        const y = priceToY(value)
        if (!smaPathStarted) {
          ctx.moveTo(x, y)
          smaPathStarted = true
        } else {
          ctx.lineTo(x, y)
        }
      }
    })
    ctx.stroke()

    // Dibujar EMA 20 (línea más delgada, color naranja)
    ctx.strokeStyle = '#F5A623'
    ctx.lineWidth = 1.5
    ctx.setLineDash([5, 5]) // Línea punteada
    ctx.beginPath()
    let emaPathStarted = false
    ema20.forEach((value, index) => {
      if (!isNaN(value)) {
        const x = indexToX(index)
        const y = priceToY(value)
        if (!emaPathStarted) {
          ctx.moveTo(x, y)
          emaPathStarted = true
        } else {
          ctx.lineTo(x, y)
        }
      }
    })
    ctx.stroke()
    ctx.setLineDash([]) // Reset

    // Dibujar línea de precio principal (línea más gruesa, color púrpura)
    ctx.strokeStyle = '#667eea'
    ctx.lineWidth = 2.5
    ctx.beginPath()
    prices.forEach((price, index) => {
      const x = indexToX(index)
      const y = priceToY(price)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Dibujar puntos en la línea de precio
    ctx.fillStyle = '#667eea'
    prices.forEach((price, index) => {
      const x = indexToX(index)
      const y = priceToY(price)
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    })

    // Labels del eje Y
    ctx.fillStyle = '#666'
    ctx.font = '11px Arial'
    ctx.textAlign = 'right'
    for (let i = 0; i <= 5; i++) {
      const value = minPrice + (priceRange / 5) * (5 - i)
      const y = padding.top + (chartHeight / 5) * i
      ctx.fillText(value.toFixed(2), padding.left - 10, y + 4)
    }

    // Título
    if (title || symbol) {
      ctx.fillStyle = '#333'
      ctx.font = 'bold 14px Arial'
      ctx.textAlign = 'center'
      ctx.fillText(title || symbol || 'Gráfico de Precios', width / 2, 15)
    }

    // Label del eje X
    ctx.fillStyle = '#666'
    ctx.font = '11px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('Tiempo', width / 2, height - 10)

    // Manejar eventos de mouse para tooltip
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      // Encontrar el punto más cercano
      let closestIndex = 0
      let minDistance = Infinity
      prices.forEach((_, index) => {
        const pointX = indexToX(index)
        const distance = Math.abs(x - pointX)
        if (distance < minDistance) {
          minDistance = distance
          closestIndex = index
        }
      })

      if (minDistance < 20) { // Solo mostrar si está cerca de un punto
        const point = data[closestIndex]
        const dateStr = typeof point.date === 'string' 
          ? point.date 
          : point.date.toLocaleDateString('es-ES')
        const ema20Val = ema20[closestIndex]
        const sma50Val = sma50[closestIndex]
        
        let tooltipText = `Fecha: ${dateStr}\nPrecio: $${point.price.toFixed(2)}`
        if (!isNaN(ema20Val)) {
          tooltipText += `\nEMA 20: $${ema20Val.toFixed(2)}`
        }
        if (!isNaN(sma50Val)) {
          tooltipText += `\nSMA 50: $${sma50Val.toFixed(2)}`
        }

        setTooltip({ x: e.clientX, y: e.clientY, text: tooltipText })
      } else {
        setTooltip(null)
      }
    }

    const handleMouseLeave = () => {
      setTooltip(null)
    }

    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      canvas.removeEventListener('mousemove', handleMouseMove)
      canvas.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [data, title, symbol, height])

  if (data.length === 0) {
    return (
      <div className="price-chart-container">
        <div className="chart-empty">
          <p>No hay datos de precio disponibles</p>
          <p className="chart-hint">Se necesitan al menos algunos puntos de datos para mostrar el gráfico</p>
        </div>
      </div>
    )
  }

  const hasEnoughDataForEMA = data.length >= 20
  const hasEnoughDataForSMA = data.length >= 50

  return (
    <div className="price-chart-container">
      <div className="chart-wrapper">
        <canvas
          ref={canvasRef}
          className="price-chart-canvas"
          style={{ height: `${height}px`, width: '100%' }}
        />
        {tooltip && (
          <div
            className="chart-tooltip"
            style={{
              left: `${tooltip.x + 10}px`,
              top: `${tooltip.y + 10}px`
            }}
          >
            {tooltip.text.split('\n').map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        )}
      </div>

      {showLegend && (
        <div className="chart-legend">
          <div className="legend-item">
            <div className="legend-line" style={{ backgroundColor: '#667eea', width: '20px', height: '2px' }}></div>
            <span>Precio</span>
          </div>
          {hasEnoughDataForEMA && (
            <div className="legend-item">
              <div className="legend-line-dashed" style={{ backgroundColor: '#F5A623', width: '20px', height: '2px' }}></div>
              <span>EMA 20</span>
            </div>
          )}
          {hasEnoughDataForSMA && (
            <div className="legend-item">
              <div className="legend-line" style={{ backgroundColor: '#4A90E2', width: '20px', height: '2px' }}></div>
              <span>SMA 50</span>
            </div>
          )}
          <button
            className="legend-toggle"
            onClick={() => setShowLegend(!showLegend)}
            aria-label={showLegend ? 'Ocultar leyenda' : 'Mostrar leyenda'}
          >
            {showLegend ? '−' : '+'}
          </button>
        </div>
      )}

      <div className="chart-info">
        <p className="info-text">
          <strong>Interpretación de cruces:</strong> Cuando EMA 20 cruza por encima de SMA 50, puede indicar una señal alcista. 
          Cuando cruza por debajo, puede indicar una señal bajista. Estas son guías visuales básicas, no recomendaciones de inversión.
        </p>
        {!hasEnoughDataForEMA && (
          <p className="info-warning">
            ⚠️ Se necesitan al menos 20 puntos de datos para mostrar EMA 20
          </p>
        )}
        {!hasEnoughDataForSMA && (
          <p className="info-warning">
            ⚠️ Se necesitan al menos 50 puntos de datos para mostrar SMA 50
          </p>
        )}
      </div>
    </div>
  )
}


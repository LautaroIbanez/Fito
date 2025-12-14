import { useRef, useEffect, useState } from 'react'
import './PriceChart.css'

interface PriceDataPoint {
  date: string | Date
  price: number
}

interface TechnicalData {
  symbol?: string
  prices: number[]
  indicators: TechnicalIndicators
  signals: TradingSignal[]
  dates: (Date | string)[]
  formatted: string
}

interface PriceChartProps {
  data: PriceDataPoint[]
  title?: string
  symbol?: string
  height?: number
  onTechnicalDataReady?: (data: TechnicalData) => void
}

interface TechnicalIndicators {
  sma5: number[]
  sma15: number[]
  rsi: number[]
  macd: {
    macd: number[]
    signal: number[]
    histogram: number[]
  }
}

interface TradingSignal {
  index: number
  type: 'buy' | 'sell'
  reason: string
  price: number
  date: Date | string
}

export default function PriceChart({ data, title, symbol, height = 300, onTechnicalDataReady }: PriceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [showLegend, setShowLegend] = useState(true)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)
  
  // Estados para toggles de indicadores
  const [showSMA5, setShowSMA5] = useState(true)
  const [showSMA15, setShowSMA15] = useState(true)
  const [showSMA50, setShowSMA50] = useState(true)
  const [showEMA20, setShowEMA20] = useState(true)
  const [showRSI, setShowRSI] = useState(false) // RSI se muestra en panel separado
  const [showMACD, setShowMACD] = useState(false) // MACD se muestra en panel separado
  const [showSignals, setShowSignals] = useState(true)

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

  // Calcular RSI (Relative Strength Index)
  const calculateRSI = (prices: number[], period: number = 14): number[] => {
    const rsi: number[] = []
    const gains: number[] = []
    const losses: number[] = []

    // Calcular cambios de precio
    for (let i = 1; i < prices.length; i++) {
      const change = prices[i] - prices[i - 1]
      gains.push(change > 0 ? change : 0)
      losses.push(change < 0 ? -change : 0)
    }

    // Calcular RSI
    for (let i = 0; i < prices.length; i++) {
      if (i < period) {
        rsi.push(NaN)
      } else {
        const avgGain = gains.slice(i - period, i).reduce((a, b) => a + b, 0) / period
        const avgLoss = losses.slice(i - period, i).reduce((a, b) => a + b, 0) / period
        
        if (avgLoss === 0) {
          rsi.push(100)
        } else {
          const rs = avgGain / avgLoss
          rsi.push(100 - (100 / (1 + rs)))
        }
      }
    }

    return rsi
  }

  // Calcular MACD (Moving Average Convergence Divergence)
  const calculateMACD = (prices: number[]): { macd: number[]; signal: number[]; histogram: number[] } => {
    const ema12 = calculateEMA(prices, 12)
    const ema26 = calculateEMA(prices, 26)
    
    const macd: number[] = []
    for (let i = 0; i < prices.length; i++) {
      if (isNaN(ema12[i]) || isNaN(ema26[i])) {
        macd.push(NaN)
      } else {
        macd.push(ema12[i] - ema26[i])
      }
    }

    // Signal line (EMA 9 del MACD) - calcular directamente sobre macd array
    const adjustedSignal: number[] = []
    const multiplier = 2 / (9 + 1) // Multiplicador para EMA 9
    
    for (let i = 0; i < macd.length; i++) {
      if (isNaN(macd[i])) {
        adjustedSignal.push(NaN)
      } else if (i === 0) {
        adjustedSignal.push(macd[i])
      } else {
        // Encontrar el último valor válido de signal
        let lastValidSignal = adjustedSignal[i - 1]
        if (isNaN(lastValidSignal)) {
          // Si el anterior es NaN, buscar el último válido o usar el MACD actual
          for (let j = i - 1; j >= 0; j--) {
            if (!isNaN(adjustedSignal[j])) {
              lastValidSignal = adjustedSignal[j]
              break
            }
          }
          if (isNaN(lastValidSignal)) {
            lastValidSignal = macd[i]
          }
        }
        adjustedSignal.push((macd[i] - lastValidSignal) * multiplier + lastValidSignal)
      }
    }

    // Histogram (MACD - Signal)
    const histogram: number[] = []
    for (let i = 0; i < macd.length; i++) {
      if (isNaN(macd[i]) || isNaN(adjustedSignal[i])) {
        histogram.push(NaN)
      } else {
        histogram.push(macd[i] - adjustedSignal[i])
      }
    }

    return { macd, signal: adjustedSignal, histogram }
  }

  // Detectar señales de trading
  const detectSignals = (
    prices: number[],
    indicators: TechnicalIndicators,
    dates: (Date | string)[]
  ): TradingSignal[] => {
    const signals: TradingSignal[] = []

    for (let i = 1; i < prices.length; i++) {
      const prevI = i - 1

      // Señal 1: Cruce de SMA5 > SMA15 (buy)
      if (!isNaN(indicators.sma5[i]) && !isNaN(indicators.sma15[i]) &&
          !isNaN(indicators.sma5[prevI]) && !isNaN(indicators.sma15[prevI])) {
        if (indicators.sma5[prevI] <= indicators.sma15[prevI] && 
            indicators.sma5[i] > indicators.sma15[i]) {
          signals.push({
            index: i,
            type: 'buy',
            reason: 'SMA5 cruza por encima de SMA15',
            price: prices[i],
            date: dates[i]
          })
        }
        // Señal: Cruce de SMA5 < SMA15 (sell)
        if (indicators.sma5[prevI] >= indicators.sma15[prevI] && 
            indicators.sma5[i] < indicators.sma15[i]) {
          signals.push({
            index: i,
            type: 'sell',
            reason: 'SMA5 cruza por debajo de SMA15',
            price: prices[i],
            date: dates[i]
          })
        }
      }

      // Señal 2: RSI < 30 (buy), RSI > 70 (sell)
      if (!isNaN(indicators.rsi[i])) {
        if (indicators.rsi[i] < 30 && (i === 0 || indicators.rsi[prevI] >= 30)) {
          signals.push({
            index: i,
            type: 'buy',
            reason: `RSI sobreventa (${indicators.rsi[i].toFixed(1)})`,
            price: prices[i],
            date: dates[i]
          })
        }
        if (indicators.rsi[i] > 70 && (i === 0 || indicators.rsi[prevI] <= 70)) {
          signals.push({
            index: i,
            type: 'sell',
            reason: `RSI sobrecompra (${indicators.rsi[i].toFixed(1)})`,
            price: prices[i],
            date: dates[i]
          })
        }
      }

      // Señal 3: MACD cruza signal line
      if (!isNaN(indicators.macd.macd[i]) && !isNaN(indicators.macd.signal[i]) &&
          !isNaN(indicators.macd.macd[prevI]) && !isNaN(indicators.macd.signal[prevI])) {
        // MACD cruza por encima de signal (buy)
        if (indicators.macd.macd[prevI] <= indicators.macd.signal[prevI] &&
            indicators.macd.macd[i] > indicators.macd.signal[i]) {
          signals.push({
            index: i,
            type: 'buy',
            reason: 'MACD cruza por encima de Signal',
            price: prices[i],
            date: dates[i]
          })
        }
        // MACD cruza por debajo de signal (sell)
        if (indicators.macd.macd[prevI] >= indicators.macd.signal[prevI] &&
            indicators.macd.macd[i] < indicators.macd.signal[i]) {
          signals.push({
            index: i,
            type: 'sell',
            reason: 'MACD cruza por debajo de Signal',
            price: prices[i],
            date: dates[i]
          })
        }
      }
    }

    return signals
  }

  // Formatear datos técnicos para el asistente IA
  const formatTechnicalDataForAI = (
    prices: number[],
    indicators: TechnicalIndicators,
    signals: TradingSignal[],
    dates: (Date | string)[]
  ): string => {
    const lastIndex = prices.length - 1
    const lastPrice = prices[lastIndex]
    const lastSMA5 = indicators.sma5[lastIndex]
    const lastSMA15 = indicators.sma15[lastIndex]
    const lastRSI = indicators.rsi[lastIndex]
    const lastMACD = indicators.macd.macd[lastIndex]
    const lastSignal = indicators.macd.signal[lastIndex]

    let output = `DATOS TÉCNICOS - ${symbol || 'Activo'}:\n`
    output += `Precio actual: ${lastPrice.toFixed(2)}\n`
    output += `SMA 5: ${!isNaN(lastSMA5) ? lastSMA5.toFixed(2) : 'N/A'}\n`
    output += `SMA 15: ${!isNaN(lastSMA15) ? lastSMA15.toFixed(2) : 'N/A'}\n`
    output += `RSI: ${!isNaN(lastRSI) ? lastRSI.toFixed(2) : 'N/A'}\n`
    output += `MACD: ${!isNaN(lastMACD) ? lastMACD.toFixed(4) : 'N/A'}\n`
    output += `Signal: ${!isNaN(lastSignal) ? lastSignal.toFixed(4) : 'N/A'}\n\n`

    if (signals.length > 0) {
      output += `SEÑALES DETECTADAS (últimas 5):\n`
      const recentSignals = signals.slice(-5)
      recentSignals.forEach((signal, idx) => {
        const dateStr = typeof signal.date === 'string' ? signal.date : signal.date.toLocaleDateString('es-ES')
        output += `${idx + 1}. ${signal.type.toUpperCase()} - ${dateStr} - ${signal.reason} - Precio: ${signal.price.toFixed(2)}\n`
      })
    } else {
      output += `No se detectaron señales de trading.\n`
    }

    return output
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

    // Calcular todos los indicadores técnicos
    const sma5 = calculateSMA(prices, 5)
    const sma15 = calculateSMA(prices, 15)
    const ema20 = calculateEMA(prices, 20)
    const sma50 = calculateSMA(prices, 50)
    const rsi = calculateRSI(prices, 14)
    const macd = calculateMACD(prices)

    const indicators: TechnicalIndicators = {
      sma5,
      sma15,
      rsi,
      macd
    }

    // Detectar señales de trading
    const signals = detectSignals(prices, indicators, dates)

    // Formatear datos para IA (disponible en consola para debugging)
    const technicalDataForAI = formatTechnicalDataForAI(prices, indicators, signals, dates)
    console.log('Technical Data for AI:', technicalDataForAI)
    
    // Exponer datos técnicos en window para acceso externo
    const technicalData = {
      symbol,
      prices,
      indicators,
      signals,
      dates,
      formatted: technicalDataForAI
    }
    ;(window as any).lastTechnicalData = technicalData
    
    // Llamar callback si está disponible
    if (onTechnicalDataReady) {
      onTechnicalDataReady(technicalData)
    }

    // Encontrar min/max para escalado (incluir todas las líneas visibles)
    const allValues = [...prices]
    if (showSMA5) allValues.push(...sma5.filter(v => !isNaN(v)))
    if (showSMA15) allValues.push(...sma15.filter(v => !isNaN(v)))
    if (showSMA50) allValues.push(...sma50.filter(v => !isNaN(v)))
    if (showEMA20) allValues.push(...ema20.filter(v => !isNaN(v)))
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

    // Dibujar SMA 5 (si está activo)
    if (showSMA5) {
      ctx.strokeStyle = '#00C853'
      ctx.lineWidth = 1.5
      ctx.setLineDash([])
      ctx.beginPath()
      let sma5PathStarted = false
      sma5.forEach((value, index) => {
        if (!isNaN(value)) {
          const x = indexToX(index)
          const y = priceToY(value)
          if (!sma5PathStarted) {
            ctx.moveTo(x, y)
            sma5PathStarted = true
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()
    }

    // Dibujar SMA 15 (si está activo)
    if (showSMA15) {
      ctx.strokeStyle = '#FF6F00'
      ctx.lineWidth = 1.5
      ctx.setLineDash([])
      ctx.beginPath()
      let sma15PathStarted = false
      sma15.forEach((value, index) => {
        if (!isNaN(value)) {
          const x = indexToX(index)
          const y = priceToY(value)
          if (!sma15PathStarted) {
            ctx.moveTo(x, y)
            sma15PathStarted = true
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()
    }

    // Dibujar SMA 50 (si está activo)
    if (showSMA50) {
      ctx.strokeStyle = '#4A90E2'
      ctx.lineWidth = 2
      ctx.setLineDash([])
      ctx.beginPath()
      let sma50PathStarted = false
      sma50.forEach((value, index) => {
        if (!isNaN(value)) {
          const x = indexToX(index)
          const y = priceToY(value)
          if (!sma50PathStarted) {
            ctx.moveTo(x, y)
            sma50PathStarted = true
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()
    }

    // Dibujar EMA 20 (si está activo)
    if (showEMA20) {
      ctx.strokeStyle = '#F5A623'
      ctx.lineWidth = 1.5
      ctx.setLineDash([5, 5]) // Línea punteada
      ctx.beginPath()
      let ema20PathStarted = false
      ema20.forEach((value, index) => {
        if (!isNaN(value)) {
          const x = indexToX(index)
          const y = priceToY(value)
          if (!ema20PathStarted) {
            ctx.moveTo(x, y)
            ema20PathStarted = true
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()
      ctx.setLineDash([]) // Reset
    }

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

    // Dibujar señales de trading (flechas)
    if (showSignals) {
      signals.forEach((signal) => {
        const x = indexToX(signal.index)
        const y = priceToY(signal.price)
        
        ctx.save()
        ctx.translate(x, y)
        
        if (signal.type === 'buy') {
          // Flecha verde hacia arriba
          ctx.fillStyle = '#00C853'
          ctx.strokeStyle = '#00C853'
          ctx.beginPath()
          ctx.moveTo(0, -15)
          ctx.lineTo(-8, 0)
          ctx.lineTo(8, 0)
          ctx.closePath()
          ctx.fill()
          ctx.stroke()
        } else {
          // Flecha roja hacia abajo
          ctx.fillStyle = '#D32F2F'
          ctx.strokeStyle = '#D32F2F'
          ctx.beginPath()
          ctx.moveTo(0, 15)
          ctx.lineTo(-8, 0)
          ctx.lineTo(8, 0)
          ctx.closePath()
          ctx.fill()
          ctx.stroke()
        }
        
        ctx.restore()
      })
    }

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
        const sma5Val = sma5[closestIndex]
        const sma15Val = sma15[closestIndex]
        const ema20Val = ema20[closestIndex]
        const sma50Val = sma50[closestIndex]
        const rsiVal = rsi[closestIndex]
        const macdVal = macd.macd[closestIndex]
        const signalVal = macd.signal[closestIndex]
        
        let tooltipText = `Fecha: ${dateStr}\nPrecio: $${point.price.toFixed(2)}`
        if (showSMA5 && !isNaN(sma5Val)) {
          tooltipText += `\nSMA 5: $${sma5Val.toFixed(2)}`
        }
        if (showSMA15 && !isNaN(sma15Val)) {
          tooltipText += `\nSMA 15: $${sma15Val.toFixed(2)}`
        }
        if (showEMA20 && !isNaN(ema20Val)) {
          tooltipText += `\nEMA 20: $${ema20Val.toFixed(2)}`
        }
        if (showSMA50 && !isNaN(sma50Val)) {
          tooltipText += `\nSMA 50: $${sma50Val.toFixed(2)}`
        }
        if (!isNaN(rsiVal)) {
          tooltipText += `\nRSI: ${rsiVal.toFixed(2)}`
        }
        if (!isNaN(macdVal) && !isNaN(signalVal)) {
          tooltipText += `\nMACD: ${macdVal.toFixed(4)}\nSignal: ${signalVal.toFixed(4)}`
        }
        
        // Mostrar señales cercanas
        const nearbySignals = signals.filter(s => Math.abs(s.index - closestIndex) <= 2)
        if (nearbySignals.length > 0) {
          tooltipText += `\n\nSeñales:`
          nearbySignals.forEach(s => {
            tooltipText += `\n${s.type.toUpperCase()}: ${s.reason}`
          })
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
  }, [data, title, symbol, height, showSMA5, showSMA15, showSMA50, showEMA20, showSignals])

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

  // Calcular indicadores y señales para la leyenda (solo si hay datos)
  let signals: TradingSignal[] = []
  if (data.length > 0) {
    const prices = data.map(d => d.price)
    const dates = data.map(d => typeof d.date === 'string' ? new Date(d.date) : d.date)
    const sma5 = calculateSMA(prices, 5)
    const sma15 = calculateSMA(prices, 15)
    const rsi = calculateRSI(prices, 14)
    const macd = calculateMACD(prices)
    const indicators: TechnicalIndicators = { sma5, sma15, rsi, macd }
    signals = detectSignals(prices, indicators, dates)
  }

  const hasEnoughDataForSMA5 = data.length >= 5
  const hasEnoughDataForSMA15 = data.length >= 15
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
          <div className="legend-section">
            <div className="legend-item">
              <div className="legend-line" style={{ backgroundColor: '#667eea', width: '20px', height: '2px' }}></div>
              <span>Precio</span>
            </div>
            {data.length >= 5 && (
              <label className="legend-item legend-toggle-item">
                <input
                  type="checkbox"
                  checked={showSMA5}
                  onChange={(e) => setShowSMA5(e.target.checked)}
                />
                <div className="legend-line" style={{ backgroundColor: '#00C853', width: '20px', height: '2px' }}></div>
                <span>SMA 5</span>
              </label>
            )}
            {data.length >= 15 && (
              <label className="legend-item legend-toggle-item">
                <input
                  type="checkbox"
                  checked={showSMA15}
                  onChange={(e) => setShowSMA15(e.target.checked)}
                />
                <div className="legend-line" style={{ backgroundColor: '#FF6F00', width: '20px', height: '2px' }}></div>
                <span>SMA 15</span>
              </label>
            )}
            {data.length >= 20 && (
              <label className="legend-item legend-toggle-item">
                <input
                  type="checkbox"
                  checked={showEMA20}
                  onChange={(e) => setShowEMA20(e.target.checked)}
                />
                <div className="legend-line-dashed" style={{ backgroundColor: '#F5A623', width: '20px', height: '2px' }}></div>
                <span>EMA 20</span>
              </label>
            )}
            {data.length >= 50 && (
              <label className="legend-item legend-toggle-item">
                <input
                  type="checkbox"
                  checked={showSMA50}
                  onChange={(e) => setShowSMA50(e.target.checked)}
                />
                <div className="legend-line" style={{ backgroundColor: '#4A90E2', width: '20px', height: '2px' }}></div>
                <span>SMA 50</span>
              </label>
            )}
          </div>
          <div className="legend-section">
            <label className="legend-item legend-toggle-item">
              <input
                type="checkbox"
                checked={showSignals}
                onChange={(e) => setShowSignals(e.target.checked)}
              />
              <span style={{ color: '#00C853' }}>🔼</span>
              <span>Buy</span>
            </label>
            <label className="legend-item legend-toggle-item">
              <input
                type="checkbox"
                checked={showSignals}
                onChange={(e) => setShowSignals(e.target.checked)}
              />
              <span style={{ color: '#D32F2F' }}>🔽</span>
              <span>Sell</span>
            </label>
            {signals.length > 0 && (
              <span className="legend-signal-count">({signals.length} señales)</span>
            )}
          </div>
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
          <strong>Indicadores técnicos:</strong> SMA 5/15 (cruces), RSI (sobrecompra/sobreventa), MACD (momentum). 
          Las flechas indican señales detectadas. Estas son guías visuales básicas, no recomendaciones de inversión.
        </p>
        {signals.length > 0 && (
          <div className="signals-summary">
            <strong>Señales detectadas:</strong> {signals.filter(s => s.type === 'buy').length} Buy, {signals.filter(s => s.type === 'sell').length} Sell
          </div>
        )}
        {!hasEnoughDataForSMA5 && (
          <p className="info-warning">
            ⚠️ Se necesitan al menos 5 puntos de datos para mostrar SMA 5
          </p>
        )}
        {!hasEnoughDataForSMA15 && (
          <p className="info-warning">
            ⚠️ Se necesitan al menos 15 puntos de datos para mostrar SMA 15
          </p>
        )}
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


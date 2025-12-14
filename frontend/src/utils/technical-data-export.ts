/**
 * Utilidades para exportar datos técnicos para el asistente IA
 */

export interface TechnicalDataExport {
  symbol?: string
  timestamp: string
  current_price: number
  indicators: {
    sma5?: number
    sma15?: number
    ema20?: number
    sma50?: number
    rsi?: number
    macd?: {
      macd: number
      signal: number
      histogram: number
    }
  }
  signals: Array<{
    type: 'buy' | 'sell'
    date: string
    price: number
    reason: string
  }>
  summary: string
}

/**
 * Obtiene los últimos datos técnicos calculados desde el gráfico
 */
export function getLastTechnicalData(): TechnicalDataExport | null {
  const data = (window as any).lastTechnicalData
  if (!data) return null

  const lastIndex = data.prices.length - 1
  const lastPrice = data.prices[lastIndex]
  const indicators = data.indicators

  return {
    symbol: data.symbol,
    timestamp: new Date().toISOString(),
    current_price: lastPrice,
    indicators: {
      sma5: indicators.sma5?.[lastIndex] ?? undefined,
      sma15: indicators.sma15?.[lastIndex] ?? undefined,
      rsi: indicators.rsi?.[lastIndex] ?? undefined,
      macd: indicators.macd?.macd?.[lastIndex] && indicators.macd?.signal?.[lastIndex]
        ? {
            macd: indicators.macd.macd[lastIndex],
            signal: indicators.macd.signal[lastIndex],
            histogram: indicators.macd.histogram?.[lastIndex] ?? 0
          }
        : undefined
    },
    signals: data.signals.slice(-10).map((s: any) => ({
      type: s.type,
      date: typeof s.date === 'string' ? s.date : s.date.toISOString(),
      price: s.price,
      reason: s.reason
    })),
    summary: data.formatted
  }
}

/**
 * Formatea los datos técnicos en un formato compacto para el asistente IA
 */
export function formatTechnicalDataForAI(data: TechnicalDataExport): string {
  let output = `=== DATOS TÉCNICOS - ${data.symbol || 'Activo'} ===\n`
  output += `Precio actual: ${data.current_price.toFixed(2)}\n`
  output += `Timestamp: ${data.timestamp}\n\n`

  output += `INDICADORES:\n`
  if (data.indicators.sma5 !== undefined) {
    output += `- SMA 5: ${data.indicators.sma5.toFixed(2)}\n`
  }
  if (data.indicators.sma15 !== undefined) {
    output += `- SMA 15: ${data.indicators.sma15.toFixed(2)}\n`
  }
  if (data.indicators.rsi !== undefined) {
    output += `- RSI: ${data.indicators.rsi.toFixed(2)} ${data.indicators.rsi < 30 ? '(Sobreventa)' : data.indicators.rsi > 70 ? '(Sobrecompra)' : ''}\n`
  }
  if (data.indicators.macd) {
    output += `- MACD: ${data.indicators.macd.macd.toFixed(4)}\n`
    output += `- Signal: ${data.indicators.macd.signal.toFixed(4)}\n`
    output += `- Histogram: ${data.indicators.macd.histogram.toFixed(4)} ${data.indicators.macd.histogram > 0 ? '(Alcista)' : '(Bajista)'}\n`
  }

  if (data.signals.length > 0) {
    output += `\nSEÑALES (últimas ${data.signals.length}):\n`
    data.signals.forEach((signal, idx) => {
      output += `${idx + 1}. ${signal.type.toUpperCase()} - ${signal.date} - ${signal.reason} - Precio: ${signal.price.toFixed(2)}\n`
    })
  } else {
    output += `\nNo se detectaron señales de trading.\n`
  }

  return output
}

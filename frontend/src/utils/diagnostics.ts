/**
 * Sistema de diagnóstico para rastrear llamadas HTTP y estados de carga
 * Ayuda a identificar qué está bloqueando el render inicial
 */

interface HttpCall {
  id: string
  method: string
  url: string
  startTime: number
  endTime?: number
  status?: number
  error?: string
  duration?: number
}

class Diagnostics {
  private httpCalls: Map<string, HttpCall> = new Map()
  private callCounter = 0
  private enabled = true

  constructor() {
    if (typeof window !== 'undefined') {
      // Habilitar en desarrollo o cuando se especifique
      this.enabled = import.meta.env.DEV || localStorage.getItem('enableDiagnostics') === 'true'
      
      if (this.enabled) {
        console.log('%c[DIAGNOSTICS] Sistema de diagnóstico activado', 'color: #1f6b47; font-weight: bold')
        this.setupGlobalErrorHandling()
      }
    }
  }

  private setupGlobalErrorHandling() {
    // Capturar errores no manejados
    window.addEventListener('error', (event) => {
      console.error('%c[DIAGNOSTICS] Error no manejado:', 'color: #dc2626; font-weight: bold', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
      })
    })

    // Capturar promesas rechazadas
    window.addEventListener('unhandledrejection', (event) => {
      console.error('%c[DIAGNOSTICS] Promesa rechazada no manejada:', 'color: #dc2626; font-weight: bold', {
        reason: event.reason,
        promise: event.promise
      })
    })
  }

  startHttpCall(method: string, url: string): string {
    if (!this.enabled) return ''
    
    const id = `http-${++this.callCounter}`
    const call: HttpCall = {
      id,
      method,
      url,
      startTime: performance.now()
    }
    
    this.httpCalls.set(id, call)
    
    console.log(
      `%c[HTTP REQUEST] ${method} ${url}`,
      'color: #2563eb; font-weight: bold',
      { id, timestamp: new Date().toISOString() }
    )
    
    return id
  }

  endHttpCall(id: string, status?: number, error?: string) {
    if (!this.enabled || !id) return
    
    const call = this.httpCalls.get(id)
    if (!call) return
    
    call.endTime = performance.now()
    call.duration = call.endTime - call.startTime
    call.status = status
    call.error = error
    
    const statusColor = status && status >= 200 && status < 300 
      ? '#1f6b47' 
      : status && status >= 400 
        ? '#dc2626' 
        : '#f59e0b'
    
    const statusText = error ? 'ERROR' : status ? `HTTP ${status}` : 'UNKNOWN'
    
    console.log(
      `%c[HTTP RESPONSE] ${call.method} ${call.url} - ${statusText} (${call.duration.toFixed(0)}ms)`,
      `color: ${statusColor}; font-weight: bold`,
      {
        id,
        duration: `${call.duration.toFixed(2)}ms`,
        status,
        error,
        timestamp: new Date().toISOString()
      }
    )
    
    // Alerta si la llamada tarda más de 5 segundos
    if (call.duration > 5000) {
      console.warn(
        `%c[DIAGNOSTICS] ⚠️ Llamada HTTP lenta detectada: ${call.method} ${call.url} (${call.duration.toFixed(0)}ms)`,
        'color: #f59e0b; font-weight: bold; font-size: 14px'
      )
    }
    
    // Alerta si hay error
    if (error || (status && status >= 400)) {
      console.error(
        `%c[DIAGNOSTICS] ❌ Error en llamada HTTP: ${call.method} ${call.url}`,
        'color: #dc2626; font-weight: bold; font-size: 14px',
        { status, error }
      )
    }
  }

  logComponentState(componentName: string, state: Record<string, any>) {
    if (!this.enabled) return
    
    console.log(
      `%c[COMPONENT STATE] ${componentName}`,
      'color: #7c3aed; font-weight: bold',
      { ...state, timestamp: new Date().toISOString() }
    )
  }

  logRenderBlock(componentName: string, reason: string, details?: any) {
    if (!this.enabled) return
    
    console.warn(
      `%c[DIAGNOSTICS] ⚠️ Render bloqueado en ${componentName}`,
      'color: #f59e0b; font-weight: bold; font-size: 14px',
      { reason, details, timestamp: new Date().toISOString() }
    )
  }

  getPendingCalls(): HttpCall[] {
    return Array.from(this.httpCalls.values())
      .filter(call => !call.endTime)
      .map(call => ({
        ...call,
        elapsed: performance.now() - call.startTime
      }))
  }

  getSlowCalls(threshold: number = 5000): HttpCall[] {
    return Array.from(this.httpCalls.values())
      .filter(call => call.duration && call.duration > threshold)
  }

  getFailedCalls(): HttpCall[] {
    return Array.from(this.httpCalls.values())
      .filter(call => call.error || (call.status && call.status >= 400))
  }

  printSummary() {
    if (!this.enabled) return
    
    const pending = this.getPendingCalls()
    const slow = this.getSlowCalls()
    const failed = this.getFailedCalls()
    const total = this.httpCalls.size
    
    console.group('%c[DIAGNOSTICS] Resumen de llamadas HTTP', 'color: #1f6b47; font-weight: bold; font-size: 16px')
    console.log(`Total de llamadas: ${total}`)
    console.log(`Pendientes: ${pending.length}`, pending)
    console.log(`Lentas (>5s): ${slow.length}`, slow)
    console.log(`Fallidas: ${failed.length}`, failed)
    console.groupEnd()
    
    if (pending.length > 0) {
      console.warn(
        `%c[DIAGNOSTICS] ⚠️ Hay ${pending.length} llamada(s) HTTP pendiente(s) que pueden estar bloqueando el render`,
        'color: #f59e0b; font-weight: bold; font-size: 14px'
      )
    }
  }

  clear() {
    this.httpCalls.clear()
    this.callCounter = 0
  }
}

// Instancia singleton
export const diagnostics = new Diagnostics()

// Exponer globalmente para acceso desde consola
if (typeof window !== 'undefined') {
  (window as any).diagnostics = diagnostics
}

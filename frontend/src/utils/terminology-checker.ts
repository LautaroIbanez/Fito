/**
 * Terminology Checker
 * 
 * Utilidad para verificar consistencia terminológica según el glosario
 * y detectar frases duplicadas o terminología mixta.
 */

// Glosario de términos estándar
export const TERMINOLOGY_GLOSSARY = {
  // Instrumentos financieros
  'bonos cer': { standard: 'Bonos CER', variants: ['bonos cer', 'Bonos Cer', 'bonos indexados'] },
  'dólar mep': { standard: 'Dólar MEP', variants: ['dólar mep', 'Dólar Mep', 'dólar mercado electrónico'] },
  'spread soberano': { standard: 'Spread soberano', variants: ['spread Soberano', 'Spread Soberano', 'diferencial soberano'] },
  'activo': { standard: 'Activo', variants: ['activo financiero', 'instrumento'] },
  'ticker': { standard: 'Ticker', variants: ['símbolo', 'código'] },
  'cartera': { standard: 'Cartera', variants: ['portafolio', 'portfolio'] },
  
  // Tipos de activos
  'acciones': { standard: 'Acciones', variants: ['acciones comunes', 'stocks'] },
  'bonos': { standard: 'Bonos', variants: ['bonos gubernamentales', 'bonos corporativos'] },
  'fx': { standard: 'FX', variants: ['divisas', 'monedas', 'forex'] },
  'commodities': { standard: 'Commodities', variants: ['materias primas', 'commodities'] },
  'sectores': { standard: 'Sectores', variants: ['industrias', 'categorías'] },
  
  // Métricas
  'confianza': { standard: 'Confianza', variants: ['nivel de confianza'] },
  'sensibilidad': { standard: 'Sensibilidad', variants: ['exposición', 'impacto'] },
  'score': { standard: 'Score', variants: ['puntuación', 'calificación'] },
  'driver': { standard: 'Driver', variants: ['factor', 'catalizador', 'motor'] },
  'escenario': { standard: 'Escenario', variants: ['situación', 'caso', 'proyección'] },
  'riesgo': { standard: 'Riesgo', variants: ['peligro', 'amenaza'] },
  'oportunidad': { standard: 'Oportunidad', variants: ['chance', 'posibilidad positiva'] },
  
  // Estados
  'alcista': { standard: 'Alcista', variants: ['bullish', 'positivo', 'al alza'] },
  'bajista': { standard: 'Bajista', variants: ['bearish', 'negativo', 'a la baja'] },
  'neutral': { standard: 'Neutral', variants: ['lateral', 'sin tendencia'] },
}

// Términos prohibidos
export const PROHIBITED_TERMS = [
  'portfolio',
  'stock',
  'bullish',
  'bearish',
  'forex',
  'commodity',
]

// Headings estándar esperados
export const STANDARD_HEADINGS = {
  'qué pasó hoy': 'Qué Pasó Hoy',
  'por qué importa': 'Por Qué Importa',
  'top 3 activos sensibles': 'Top 3 Activos Sensibles',
  'escenarios': 'Escenarios',
  'acciones rápidas': 'Acciones Rápidas',
}

// Frases estándar
export const STANDARD_PHRASES = {
  loading: [
    'Cargando...',
    'Generando síntesis...',
    'Generando escenarios...',
    'Analizando relevancia...',
  ],
  empty: [
    'No hay datos disponibles',
    'No hay noticias recientes',
    'No hay activos sensibles identificados',
    'No se generaron escenarios',
  ],
  error: [
    'Error al cargar datos',
    'Error al generar síntesis',
    'Timeout: La generación excedió',
    'No se pudieron cargar los escenarios',
  ],
}

interface TerminologyIssue {
  type: 'variant' | 'prohibited' | 'capitalization' | 'duplicate'
  term: string
  found: string
  suggested: string
  location?: string
}

/**
 * Verifica un texto contra el glosario
 */
export function checkTerminology(text: string, location?: string): TerminologyIssue[] {
  const issues: TerminologyIssue[] = []
  const lowerText = text.toLowerCase()
  
  // Verificar variantes
  for (const [key, entry] of Object.entries(TERMINOLOGY_GLOSSARY)) {
    for (const variant of entry.variants) {
      if (lowerText.includes(variant.toLowerCase())) {
        issues.push({
          type: 'variant',
          term: key,
          found: variant,
          suggested: entry.standard,
          location,
        })
      }
    }
  }
  
  // Verificar términos prohibidos
  for (const prohibited of PROHIBITED_TERMS) {
    if (lowerText.includes(prohibited)) {
      issues.push({
        type: 'prohibited',
        term: prohibited,
        found: prohibited,
        suggested: getReplacement(prohibited),
        location,
      })
    }
  }
  
  return issues
}

/**
 * Verifica capitalización de headings
 */
export function checkHeadingCapitalization(heading: string, location?: string): TerminologyIssue[] {
  const issues: TerminologyIssue[] = []
  const lowerHeading = heading.toLowerCase().trim()
  
  // Verificar si el heading está en el estándar
  if (STANDARD_HEADINGS[lowerHeading]) {
    const expected = STANDARD_HEADINGS[lowerHeading]
    if (heading !== expected) {
      issues.push({
        type: 'capitalization',
        term: 'heading',
        found: heading,
        suggested: expected,
        location,
      })
    }
  }
  
  // Verificar Title Case (primera letra de cada palabra importante)
  const words = heading.split(' ')
  const importantWords = ['qué', 'por', 'top', 'activos', 'sensibles', 'escenarios', 'acciones', 'rápidas']
  
  for (let i = 0; i < words.length; i++) {
    const word = words[i]
    const lowerWord = word.toLowerCase()
    
    // Primera palabra siempre en mayúscula
    if (i === 0 && word[0] !== word[0].toUpperCase()) {
      issues.push({
        type: 'capitalization',
        term: 'heading',
        found: heading,
        suggested: capitalizeFirst(heading),
        location,
      })
      break
    }
    
    // Palabras importantes deben estar en Title Case
    if (importantWords.includes(lowerWord) && word[0] !== word[0].toUpperCase()) {
      issues.push({
        type: 'capitalization',
        term: 'heading',
        found: heading,
        suggested: applyTitleCase(heading),
        location,
      })
      break
    }
  }
  
  return issues
}

/**
 * Detecta frases duplicadas en un array de textos
 */
export function detectDuplicates(texts: string[]): TerminologyIssue[] {
  const issues: TerminologyIssue[] = []
  const seen = new Map<string, number[]>()
  
  texts.forEach((text, index) => {
    const normalized = text.toLowerCase().trim()
    if (seen.has(normalized)) {
      seen.get(normalized)!.push(index)
    } else {
      seen.set(normalized, [index])
    }
  })
  
  seen.forEach((indices, text) => {
    if (indices.length > 1) {
      issues.push({
        type: 'duplicate',
        term: text,
        found: text,
        suggested: `Frase duplicada ${indices.length} veces en índices: ${indices.join(', ')}`,
        location: `Índices: ${indices.join(', ')}`,
      })
    }
  })
  
  return issues
}

/**
 * Obtiene reemplazo para término prohibido
 */
function getReplacement(term: string): string {
  const replacements: Record<string, string> = {
    'portfolio': 'Cartera',
    'stock': 'Acciones',
    'bullish': 'Alcista',
    'bearish': 'Bajista',
    'forex': 'FX',
    'commodity': 'Commodities',
  }
  return replacements[term] || term
}

/**
 * Capitaliza primera letra
 */
function capitalizeFirst(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/**
 * Aplica Title Case
 */
function applyTitleCase(text: string): string {
  const words = text.split(' ')
  const importantWords = ['qué', 'por', 'top', 'activos', 'sensibles', 'escenarios', 'acciones', 'rápidas']
  
  return words.map((word, index) => {
    const lowerWord = word.toLowerCase()
    if (index === 0 || importantWords.includes(lowerWord)) {
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    }
    return word
  }).join(' ')
}

/**
 * Verifica todos los headings en un componente
 */
export function checkComponentHeadings(headings: Record<string, string>): TerminologyIssue[] {
  const issues: TerminologyIssue[] = []
  
  for (const [location, heading] of Object.entries(headings)) {
    issues.push(...checkHeadingCapitalization(heading, location))
    issues.push(...checkTerminology(heading, location))
  }
  
  return issues
}

/**
 * Genera reporte de inconsistencias
 */
export function generateReport(issues: TerminologyIssue[]): string {
  if (issues.length === 0) {
    return '✅ No se encontraron inconsistencias terminológicas.'
  }
  
  const report = ['⚠️ Inconsistencias terminológicas encontradas:\n']
  
  const byType = issues.reduce((acc, issue) => {
    if (!acc[issue.type]) acc[issue.type] = []
    acc[issue.type].push(issue)
    return acc
  }, {} as Record<string, TerminologyIssue[]>)
  
  for (const [type, typeIssues] of Object.entries(byType)) {
    report.push(`\n${type.toUpperCase()} (${typeIssues.length}):`)
    typeIssues.forEach(issue => {
      report.push(`  - "${issue.found}" → "${issue.suggested}"`)
      if (issue.location) {
        report.push(`    Ubicación: ${issue.location}`)
      }
    })
  }
  
  return report.join('\n')
}


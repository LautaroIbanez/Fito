/**
 * Tests for AssistantWidget component
 * 
 * NOTE: This test file requires testing dependencies to be installed:
 * - @testing-library/react
 * - @testing-library/jest-dom
 * - @testing-library/user-event
 * - vitest (or jest)
 * 
 * Install with: npm install --save-dev @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AssistantWidget from '../AssistantWidget'
import { newsApi } from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  newsApi: {
    getNewsSummaries: vi.fn(),
  },
}))

describe('AssistantWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Manual Analysis Trigger', () => {
    it('should NOT run analysis automatically on mount', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue({
        summaries: [],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 0,
      })

      render(<AssistantWidget />)

      // Wait a bit to ensure useEffect has run
      await new Promise(resolve => setTimeout(resolve, 100))

      // Verify API was NOT called automatically
      expect(newsApi.getNewsSummaries).not.toHaveBeenCalled()
    })

    it('should show "Analizar" button in header', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue({
        summaries: [],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 0,
      })

      render(<AssistantWidget />)

      await waitFor(() => {
        const analyzeButton = screen.getByRole('button', { name: /analizar/i })
        expect(analyzeButton).toBeInTheDocument()
      })
    })

    it('should show empty state with hint to click "Analizar"', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue({
        summaries: [],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 0,
      })

      render(<AssistantWidget />)

      await waitFor(() => {
        expect(screen.getByText(/no hay análisis disponible/i)).toBeInTheDocument()
        expect(screen.getByText(/haz clic en "analizar"/i)).toBeInTheDocument()
      })
    })

    it('should trigger analysis when "Analizar" button is clicked', async () => {
      const mockResponse = {
        summaries: [
          {
            news_id: 1,
            news_title: 'Test News',
            summary: 'Test summary',
            explanation: 'Test explanation',
            score: 5.0,
            sentiment: 'positive',
          },
        ],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 1,
      }

      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue(mockResponse)

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        expect(newsApi.getNewsSummaries).toHaveBeenCalledTimes(1)
      })
    })

    it('should show loading state during analysis', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          summaries: [],
          portfolio_impacts: [],
          suggestions: [],
          generated_at: '2024-01-01',
          news_count: 0,
        }), 100))
      )

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(/generando análisis/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /analizar/i })).toBeDisabled()
      })
    })

    it('should disable "Analizar" button during loading', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          summaries: [],
          portfolio_impacts: [],
          suggestions: [],
          generated_at: '2024-01-01',
          news_count: 0,
        }), 100))
      )

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        const disabledButton = screen.getByRole('button', { name: /analizar/i })
        expect(disabledButton).toBeDisabled()
      })
    })

    it('should display results after successful manual analysis', async () => {
      const mockResponse = {
        summaries: [
          {
            news_id: 1,
            news_title: 'Test News Title',
            summary: 'Test summary text',
            explanation: 'Test explanation text',
            score: 5.5,
            sentiment: 'positive',
          },
        ],
        portfolio_impacts: [
          {
            type: 'positive' as const,
            description: 'Test impact description',
            affected_assets: ['AAPL'],
          },
        ],
        suggestions: [
          {
            action: 'add' as const,
            description: 'Test suggestion',
            tone: 'positive' as const,
          },
        ],
        generated_at: '2024-01-01',
        news_count: 1,
      }

      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue(mockResponse)

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(/test news title/i)).toBeInTheDocument()
        expect(screen.getByText(/test summary text/i)).toBeInTheDocument()
        expect(screen.getByText(/test impact description/i)).toBeInTheDocument()
        expect(screen.getByText(/test suggestion/i)).toBeInTheDocument()
      })
    })

    it('should return to idle state after analysis completes', async () => {
      const mockResponse = {
        summaries: [
          {
            news_id: 1,
            news_title: 'Test News',
            summary: 'Test summary',
            explanation: 'Test explanation',
            score: 5.0,
            sentiment: 'positive',
          },
        ],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 1,
      }

      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue(mockResponse)

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        // Loading should be gone
        expect(screen.queryByText(/generando análisis/i)).not.toBeInTheDocument()
        // Button should be enabled again
        const enabledButton = screen.getByRole('button', { name: /analizar/i })
        expect(enabledButton).not.toBeDisabled()
        // Results should be displayed
        expect(screen.getByText(/test news/i)).toBeInTheDocument()
      })
    })

    it('should handle errors gracefully and return to idle state', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockRejectedValue(new Error('API Error'))

      render(<AssistantWidget />)

      const analyzeButton = screen.getByRole('button', { name: /analizar/i })
      fireEvent.click(analyzeButton)

      await waitFor(() => {
        // Should show error state
        expect(screen.getByText(/servicio no disponible/i)).toBeInTheDocument()
        // Button should be enabled again
        const enabledButton = screen.getByRole('button', { name: /analizar/i })
        expect(enabledButton).not.toBeDisabled()
      })
    })

    it('should not trigger analysis when refreshTrigger changes if no manual trigger occurred', async () => {
      vi.mocked(newsApi.getNewsSummaries).mockResolvedValue({
        summaries: [],
        portfolio_impacts: [],
        suggestions: [],
        generated_at: '2024-01-01',
        news_count: 0,
      })

      const { rerender } = render(<AssistantWidget refreshTrigger={0} />)

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(newsApi.getNewsSummaries).not.toHaveBeenCalled()

      // Change refreshTrigger
      rerender(<AssistantWidget refreshTrigger={1} />)

      await new Promise(resolve => setTimeout(resolve, 100))

      // Should still not trigger automatically
      expect(newsApi.getNewsSummaries).not.toHaveBeenCalled()
    })
  })
})


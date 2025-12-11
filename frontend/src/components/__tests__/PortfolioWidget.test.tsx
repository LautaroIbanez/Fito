/**
 * Tests for PortfolioWidget component
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
import PortfolioWidget from '../PortfolioWidget'
import { portfolioApi } from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  portfolioApi: {
    list: vi.fn(),
    create: vi.fn(),
    clearAll: vi.fn(),
    getRiskDashboard: vi.fn(),
  },
}))

describe('PortfolioWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Button Visibility', () => {
    it('should render "Agregar" button in header', async () => {
      vi.mocked(portfolioApi.list).mockResolvedValue([])
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 0,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 0 },
      })

      render(<PortfolioWidget />)

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        expect(addButton).toBeInTheDocument()
      })
    })

    it('should render "Borrar todo" button when portfolio has items', async () => {
      const mockItems = [
        { id: 1, asset_type: 'acciones', name: 'Test Asset', created_at: '2024-01-01', updated_at: '2024-01-01' },
      ]
      vi.mocked(portfolioApi.list).mockResolvedValue(mockItems as any)
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 1000,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 1000 },
      })

      render(<PortfolioWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        expect(clearButton).toBeInTheDocument()
      })
    })

    it('should not render "Borrar todo" button when portfolio is empty', async () => {
      vi.mocked(portfolioApi.list).mockResolvedValue([])
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 0,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 0 },
      })

      render(<PortfolioWidget />)

      await waitFor(() => {
        const clearButton = screen.queryByRole('button', { name: /borrar todo/i })
        expect(clearButton).not.toBeInTheDocument()
      })
    })
  })

  describe('Add Item Flow', () => {
    it('should open form when "Agregar" button is clicked', async () => {
      vi.mocked(portfolioApi.list).mockResolvedValue([])
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 0,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 0 },
      })

      render(<PortfolioWidget />)

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        fireEvent.click(addButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/nuevo item/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/categoría/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument()
      })
    })

    it('should save new item when form is submitted with valid data', async () => {
      const mockNewItem = {
        id: 1,
        asset_type: 'acciones',
        name: 'New Asset',
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      }

      vi.mocked(portfolioApi.list).mockResolvedValue([])
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 0,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 0 },
      })
      vi.mocked(portfolioApi.create).mockResolvedValue(mockNewItem as any)

      render(<PortfolioWidget />)

      // Open form
      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        fireEvent.click(addButton)
      })

      // Fill form
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/nombre/i)
        fireEvent.change(nameInput, { target: { value: 'New Asset' } })
      })

      // Submit form
      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /guardar/i })
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(portfolioApi.create).toHaveBeenCalledWith(
          expect.objectContaining({
            asset_type: 'acciones',
            name: 'New Asset',
          })
        )
      })
    })
  })

  describe('Clear All Flow', () => {
    it('should show confirmation dialog when "Borrar todo" is clicked', async () => {
      const mockItems = [
        { id: 1, asset_type: 'acciones', name: 'Test Asset', created_at: '2024-01-01', updated_at: '2024-01-01' },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

      vi.mocked(portfolioApi.list).mockResolvedValue(mockItems as any)
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 1000,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 1000 },
      })

      render(<PortfolioWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        fireEvent.click(clearButton)
      })

      expect(confirmSpy).toHaveBeenCalled()
      expect(portfolioApi.clearAll).not.toHaveBeenCalled()

      confirmSpy.mockRestore()
    })

    it('should clear all items when confirmation is accepted', async () => {
      const mockItems = [
        { id: 1, asset_type: 'acciones', name: 'Test Asset', created_at: '2024-01-01', updated_at: '2024-01-01' },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      vi.mocked(portfolioApi.list)
        .mockResolvedValueOnce(mockItems as any)
        .mockResolvedValueOnce([])
      vi.mocked(portfolioApi.getRiskDashboard)
        .mockResolvedValueOnce({
          portfolio_value: 1000,
          exposure_by_asset: [],
          exposure_by_sector: [],
          top_concentrations: [],
          volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
          var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 1000 },
        })
        .mockResolvedValueOnce({
          portfolio_value: 0,
          exposure_by_asset: [],
          exposure_by_sector: [],
          top_concentrations: [],
          volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
          var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 0 },
        })
      vi.mocked(portfolioApi.clearAll).mockResolvedValue([])

      render(<PortfolioWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        fireEvent.click(clearButton)
      })

      await waitFor(() => {
        expect(portfolioApi.clearAll).toHaveBeenCalled()
      })

      confirmSpy.mockRestore()
    })

    it('should disable buttons during clearing operation', async () => {
      const mockItems = [
        { id: 1, asset_type: 'acciones', name: 'Test Asset', created_at: '2024-01-01', updated_at: '2024-01-01' },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      vi.mocked(portfolioApi.list).mockResolvedValue(mockItems as any)
      vi.mocked(portfolioApi.getRiskDashboard).mockResolvedValue({
        portfolio_value: 1000,
        exposure_by_asset: [],
        exposure_by_sector: [],
        top_concentrations: [],
        volatility: { volatility_30d: 0, volatility_90d: 0, annual_volatility: 0 },
        var: { var_30d_95: 0, var_30d_99: 0, var_90d_95: 0, var_90d_99: 0, portfolio_value: 1000 },
      })
      vi.mocked(portfolioApi.clearAll).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 100))
      )

      render(<PortfolioWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        fireEvent.click(clearButton)
      })

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        expect(addButton).toBeDisabled()
      })

      confirmSpy.mockRestore()
    })
  })
})


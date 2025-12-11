/**
 * Tests for NewsWidget component
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
import NewsWidget from '../NewsWidget'
import { newsApi } from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  newsApi: {
    list: vi.fn(),
    create: vi.fn(),
    clearAll: vi.fn(),
  },
}))

describe('NewsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Button Visibility', () => {
    it('should render "Agregar" button in header', async () => {
      vi.mocked(newsApi.list).mockResolvedValue([])

      render(<NewsWidget />)

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        expect(addButton).toBeInTheDocument()
      })
    })

    it('should render "Borrar todo" button when news list has items', async () => {
      const mockItems = [
        { 
          id: 1, 
          body: 'Test news body content ' + 'x'.repeat(200), 
          created_at: '2024-01-01',
          title: 'Test News',
        },
      ]
      vi.mocked(newsApi.list).mockResolvedValue(mockItems as any)

      render(<NewsWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        expect(clearButton).toBeInTheDocument()
      })
    })

    it('should not render "Borrar todo" button when news list is empty', async () => {
      vi.mocked(newsApi.list).mockResolvedValue([])

      render(<NewsWidget />)

      await waitFor(() => {
        const clearButton = screen.queryByRole('button', { name: /borrar todo/i })
        expect(clearButton).not.toBeInTheDocument()
      })
    })
  })

  describe('Add News Flow', () => {
    it('should open form when "Agregar" button is clicked', async () => {
      vi.mocked(newsApi.list).mockResolvedValue([])

      render(<NewsWidget />)

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        fireEvent.click(addButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/nueva noticia/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/cuerpo de la noticia/i)).toBeInTheDocument()
      })
    })

    it('should save new news item when form is submitted with valid data', async () => {
      const mockNewItem = {
        id: 1,
        body: 'Test news body content ' + 'x'.repeat(200),
        created_at: '2024-01-01',
        title: 'New News',
      }

      vi.mocked(newsApi.list).mockResolvedValue([])
      vi.mocked(newsApi.create).mockResolvedValue(mockNewItem as any)

      render(<NewsWidget />)

      // Open form
      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        fireEvent.click(addButton)
      })

      // Fill form
      await waitFor(() => {
        const bodyTextarea = screen.getByLabelText(/cuerpo de la noticia/i)
        fireEvent.change(bodyTextarea, { target: { value: 'Test news body content ' + 'x'.repeat(200) } })
      })

      // Submit form
      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /guardar/i })
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(newsApi.create).toHaveBeenCalledWith(
          expect.objectContaining({
            body: expect.stringContaining('Test news body content'),
          })
        )
      })
    })

    it('should show error when body is too short', async () => {
      vi.mocked(newsApi.list).mockResolvedValue([])

      render(<NewsWidget />)

      // Open form
      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /agregar/i })
        fireEvent.click(addButton)
      })

      // Fill form with short body
      await waitFor(() => {
        const bodyTextarea = screen.getByLabelText(/cuerpo de la noticia/i)
        fireEvent.change(bodyTextarea, { target: { value: 'Short text' } })
      })

      // Try to submit form
      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /guardar/i })
        expect(saveButton).toBeDisabled()
      })
    })
  })

  describe('Clear All Flow', () => {
    it('should show confirmation dialog when "Borrar todo" is clicked', async () => {
      const mockItems = [
        { 
          id: 1, 
          body: 'Test news body content ' + 'x'.repeat(200), 
          created_at: '2024-01-01',
        },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

      vi.mocked(newsApi.list).mockResolvedValue(mockItems as any)

      render(<NewsWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        fireEvent.click(clearButton)
      })

      expect(confirmSpy).toHaveBeenCalled()
      expect(newsApi.clearAll).not.toHaveBeenCalled()

      confirmSpy.mockRestore()
    })

    it('should clear all news when confirmation is accepted', async () => {
      const mockItems = [
        { 
          id: 1, 
          body: 'Test news body content ' + 'x'.repeat(200), 
          created_at: '2024-01-01',
        },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      vi.mocked(newsApi.list)
        .mockResolvedValueOnce(mockItems as any)
        .mockResolvedValueOnce([])
      vi.mocked(newsApi.clearAll).mockResolvedValue([])

      render(<NewsWidget />)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /borrar todo/i })
        fireEvent.click(clearButton)
      })

      await waitFor(() => {
        expect(newsApi.clearAll).toHaveBeenCalled()
      })

      confirmSpy.mockRestore()
    })

    it('should disable buttons during clearing operation', async () => {
      const mockItems = [
        { 
          id: 1, 
          body: 'Test news body content ' + 'x'.repeat(200), 
          created_at: '2024-01-01',
        },
      ]
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      vi.mocked(newsApi.list).mockResolvedValue(mockItems as any)
      vi.mocked(newsApi.clearAll).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 100))
      )

      render(<NewsWidget />)

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


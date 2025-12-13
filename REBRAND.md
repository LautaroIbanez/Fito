# Faro Rebrand - Design System Documentation

## Brand Identity

**Brand Name:** Faro (Lighthouse in Spanish/Portuguese)  
**Tagline:** Confident Investment Intelligence  
**Brand Values:** Trust, Confidence, Guidance, Clarity

## Design Philosophy

Faro embodies a confidence-forward brand with a minimalist, trustworthy aesthetic. The design system emphasizes:

- **Trust:** Deep navy palette conveys stability and professionalism
- **Clarity:** Minimalist interface reduces cognitive load
- **Confidence:** Strategic use of accent greens signals positive action
- **Calm:** Soft neutrals create a peaceful, focused environment

## Color Palette

### Primary Colors - Deep Navy
- `--color-navy-900`: #0a1929 (Primary dark)
- `--color-navy-800`: #132f4c (Secondary dark)
- `--color-navy-700`: #1e4976 (Tertiary dark)
- `--color-navy-600`: #2e5984 (Accent dark)
- `--color-navy-500`: #3d6a97 (Light accent)

### Neutral Grays
- `--color-gray-50` to `--color-gray-900`: Full grayscale palette
- Used for backgrounds, borders, and text hierarchy

### Accent Green (Limited Use)
- `--color-green-500`: #2d8659 (Primary accent)
- `--color-green-600`: #1f6b47 (Hover states)
- `--color-green-700`: #175a3a (Active states)

**Usage Guidelines:**
- Green is reserved for primary CTAs and positive indicators
- Use sparingly to maintain impact
- Never use green for decorative elements

## Typography

### Font Families
- **Base:** System font stack (San Francisco, Segoe UI, Roboto)
- **Monospace:** SF Mono, Monaco, Courier New

### Font Sizes
- `--font-size-xs`: 0.75rem (12px)
- `--font-size-sm`: 0.875rem (14px)
- `--font-size-base`: 1rem (16px)
- `--font-size-lg`: 1.125rem (18px)
- `--font-size-xl`: 1.25rem (20px)
- `--font-size-2xl`: 1.5rem (24px)
- `--font-size-3xl`: 1.875rem (30px)
- `--font-size-4xl`: 2.25rem (36px)

### Font Weights
- Normal: 400
- Medium: 500
- Semibold: 600
- Bold: 700

## Spacing Scale

Consistent 4px base unit:
- `--spacing-1`: 4px
- `--spacing-2`: 8px
- `--spacing-3`: 12px
- `--spacing-4`: 16px
- `--spacing-5`: 20px
- `--spacing-6`: 24px
- `--spacing-8`: 32px
- `--spacing-10`: 40px
- `--spacing-12`: 48px
- `--spacing-16`: 64px
- `--spacing-20`: 80px

## Border Radius

- `--radius-sm`: 6px
- `--radius-md`: 8px
- `--radius-lg`: 12px
- `--radius-xl`: 16px
- `--radius-full`: 9999px

## Shadows

- `--shadow-sm`: Subtle elevation
- `--shadow-md`: Standard cards
- `--shadow-lg`: Elevated panels
- `--shadow-xl`: Modals and overlays

## Component Updates

### Primary CTA Buttons
- Background: `var(--color-green-600)`
- Hover: `var(--color-green-700)`
- Text: White
- Shadow: `var(--shadow-sm)` on hover

### Cards/Panels
- Background: `var(--bg-primary)` (white)
- Border: `var(--border-light)`
- Shadow: `var(--shadow-lg)`
- Hover: `var(--shadow-xl)`

### Header
- Background: Navy gradient (`var(--bg-gradient)`)
- Text: White
- Typography: Bold, large scale

## Responsive Breakpoints

- **Mobile:** < 768px
- **Tablet:** 768px - 1200px
- **Desktop:** > 1200px

## Accessibility

### Contrast Ratios
All color combinations meet WCAG AA standards:
- Text on white: 4.5:1 minimum
- Text on navy: 4.5:1 minimum
- Interactive elements: 3:1 minimum

### Focus States
- Outline: 2px solid `var(--color-green-600)`
- Offset: 2px

### High Contrast Mode
- Borders: 2-3px solid
- Increased contrast for all elements

### Reduced Motion
- Animations disabled when `prefers-reduced-motion: reduce`
- Transitions set to 0.01ms

## Implementation Checklist

- [x] Design tokens created (`design-tokens.css`)
- [x] Metadata updated (title, description, OG tags)
- [x] App header updated with new branding
- [x] Primary CSS files migrated to tokens
- [x] Primary CTA buttons updated
- [x] Cards/panels updated
- [x] Responsive design validated
- [x] Test suite created

## Migration Notes

### Old Color References
Replace these throughout the codebase:
- `#667eea` → `var(--color-green-600)`
- `#764ba2` → `var(--color-navy-800)`
- `#e0e0e0` → `var(--border-light)`
- `#1a1a1a` → `var(--text-primary)`

### Gradient Updates
- Old: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- New: `var(--bg-gradient)` or `linear-gradient(135deg, var(--color-navy-800) 0%, var(--color-navy-900) 100%)`

## Testing

Run visual regression tests:
```bash
npm test -- Branding.test.tsx
```

Test coverage includes:
- Brand name and tagline display
- Design token application
- Responsive breakpoints
- Accessibility features
- Color contrast ratios

## Future Enhancements

- [ ] Dark mode support (tokens already prepared)
- [ ] Brand icon/logo
- [ ] Custom font loading (optional)
- [ ] Animation system
- [ ] Component library documentation



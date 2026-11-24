---
name: Tech Mart Marketplace
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434653'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#747685'
  outline-variant: '#c4c5d5'
  surface-tint: '#2e56c6'
  primary: '#003092'
  on-primary: '#ffffff'
  primary-container: '#1a47b8'
  on-primary-container: '#b2c2ff'
  inverse-primary: '#b5c4ff'
  secondary: '#855300'
  on-secondary: '#ffffff'
  secondary-container: '#fea619'
  on-secondary-container: '#684000'
  tertiary: '#00432c'
  on-tertiary: '#ffffff'
  tertiary-container: '#005d3f'
  on-tertiary-container: '#4bdca0'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b5c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#023cae'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '800'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  price-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 32px
    letterSpacing: -0.01em
  price-card:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 22px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-md: 1.5rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 2rem
  margin-lg: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system targets Indian consumer electronics shoppers seeking reliability, transparency, and high-value purchases (smartphones, computing, home appliances, audio, and accessories). The tone balances technological precision with everyday consumer accessibility. 

The aesthetic blends **Modern Corporate** with **High-Utility E-Commerce**:
- **Trust & Credibility:** Strong architectural layouts with clear visual proof points (authorized reseller badges, genuine warranty seals, secure transaction cues).
- **Localized E-Commerce Cues:** Prominent pincode delivery estimators, clear EMI breakdown components, exchange value calculators, and explicit GST invoice cues.
- **Clarity Over Clutter:** Open layout breathing room, sharp contrast ratios, and structured information chunking that avoids visual fatigue during comparison shopping.

## Colors
The palette leverages deep royal navy and cobalt for authority, complemented by functional mercantile accents:

- **Primary (`#1A47B8` & `#0F2D7A`):** Core brand actions, primary navigation bars, active filter states, verified badges, and primary buttons.
- **Cobalt Highlight (`#2563EB`):** Interactive links, focus indicators, secondary callouts, and progress bars.
- **Secondary / Amber (`#F59E0B`):** Star ratings, limited-time flash deal tags, discount percentages, and festival sale highlights.
- **Tertiary / Emerald (`#10B981`):** In-stock notifications, bank offer cashbacks, price drop callouts, and successful delivery timelines.
- **Canvas & Neutral Surfaces:** 
  - Canvas base: Soft warm ivory/slate (`#FAF9F6` to `#F8FAFC`) to minimize glare during extended browsing.
  - Card & Container: Crisp white (`#FFFFFF`) for distinct content grouping.
  - Text & Form Elements: Deep slate navy (`#0F172A`) for high legibility, with muted slate (`#64748B`) for secondary metadata and MRP strike-throughs.

## Typography
- **Headlines (`Plus Jakarta Sans`):** Modern geometric shapes with humanized terminals provide an energetic, premium retail atmosphere. Used across merchandising banners, category titles, and PDP headers.
- **Body & Numerical Price Data (`Inter` & `Plus Jakarta Sans`):** Inter delivers neutral, high x-height rendering for technical specifications, terms, and delivery inputs.
- **Currency (`₹` / INR formatting):** All prices utilize tabular lining figures (`font-variant-numeric: tabular-nums`) to align prices across lists and tables cleanly. Strikethrough MRP uses standard body sizing in muted slate gray, accompanied immediately by emerald savings percentages.

## Layout & Spacing
A fluid 12-column responsive grid on desktop adapts to a dense 4-column structure on mobile devices to preserve screen estate for product cards and filters:

- **Desktop (1200px+):** Max-width 1280px container, centered. Fixed 280px left sidebar for multi-tier filtering; 12-column flow for search grids (4 items per row) and PDP layouts (60/40 gallery-to-buy-box ratio).
- **Tablet (768px - 1199px):** 8-column layout. Collapsible horizontal slide-over filter drawer, 3 product cards per row.
- **Mobile (< 768px):** 4-column layout with 2-column product grid or single-column compact list view. Sticky bottom action bar for primary PDP triggers ("Add to Cart" / "Buy Now").
- **Spacing Scale:** Built on a 4px base rhythm (`0.25rem`), prioritizing tight, dense metadata presentation in comparison specs and generous margin buffers between retail campaigns.

## Elevation & Depth
This design system avoids heavy shadows, using **clean tonal layering and low-contrast borders** suited for high-density transactional shopping:

- **Base Layer (Level 0):** Neutral `#FAF9F6` / `#F8FAFC` page background.
- **Surface Layer (Level 1):** Solid white (`#FFFFFF`) cards and panels bounded by a subtle outline: `1px solid rgba(15, 23, 42, 0.08)`.
- **Raised Interactive Layer (Level 2):** Applied to active product cards on hover, quick-view popovers, and sticky header bars. Shadow: `0 4px 12px -2px rgba(15, 45, 122, 0.08), 0 2px 6px -1px rgba(15, 45, 122, 0.04)`.
- **Overlay & Modal Layer (Level 3):** Applied to pincode selectors, image zoom lightboxes, and checkout sheets. Shadow: `0 16px 32px -4px rgba(15, 45, 122, 0.16)`. Accompanied by a `backdrop-filter: blur(4px)` over a `rgba(15, 23, 42, 0.4)` scrim.

## Shapes
A balanced **Rounded (`roundedness: 2`)** aesthetic conveys consumer-tech modernity without sacrificing corporate trustworthiness:

- **Buttons, Text Inputs, and Select Boxes:** `0.5rem` (8px) border radius for approachable, clean ergonomics.
- **Cards and Grouping Panels:** `0.75rem` to `1rem` (12px to 16px) for distinct structural containment.
- **Badges, Pills, and Tags:** Full pill radius (`9999px`) for discount tags, "Brand Authorized" badges, and stock chips to contrast against rectangular cards.
- **Checkboxes & Segmented Toggles:** `0.25rem` (4px) soft corners for precision.

## Components

### Buttons
- **Primary ("Buy Now", Checkout):** Solid `#1A47B8` background, white text, bold font-weight. Hover shifts to `#0F2D7A`. Focus ring: 2px offset with `#2563EB`.
- **Secondary ("Add to Cart"):** White background with a 1.5px `#1A47B8` border and `#1A47B8` label. Hover fills with 6% opacity navy tint.
- **Tertiary / Action Link:** Borderless text button in `#2563EB` with trailing icon (e.g., "View all bank offers →").
- **Urgent Action / Fast Checkout:** Soft amber highlight background (`#FEF3C7`) with deep amber text (`#B45309`) for instant EMI pre-approval cues.

### Product Cards
- Contained white boxes with 1px border.
- Features top badge container (e.g., emerald "Save ₹4,500" or amber "Deal of the Day").
- Square 1:1 aspect ratio image container with neutral off-white background (`#F8FAFC`).
- Title clamped to 2 lines, followed by star rating row (`#F59E0B` icons + count).
- Price stack: Current Selling Price (large, bold), Strike-through MRP (muted small), Discount percentage (emerald bold).
- Micro-delivery cue: "Get it by Tomorrow, 2 PM" in bold emerald.

### Pincode Delivery Checker
- Inline input with pincode icon, 6-digit numeric field, and embedded primary text button ("Check").
- Success state displays a clean green check icon, formatted city/region, standard delivery date, and eligible express slots.

### Chips & Badges
- **Status / Savings Chips:** Pill-shaped, subtle pastel backgrounds with deep foregrounds:
  - Green Chip: `#ECFDF5` background, `#065F46` text ("In Stock", "₹2,000 Off with HDFC").
  - Amber Chip: `#FFFBEB` background, `#92400E` text ("4.8 ★", "Limited Stock").
  - Blue Chip: `#EFF6FF` background, `#1E40AF` text ("Official Indian Warranty").

### Input Fields & Selects
- Height: 44px (touch friendly).
- Border: 1px solid `#CBD5E1`. On focus: 1.5px solid `#1A47B8` with an ambient glow (`0 0 0 3px rgba(26, 71, 184, 0.15)`).
- Error state: `#DC2626` outline and helper text.

### EMI & Bank Offer Accordion
- Structured card with a light blue tinted left-accent border (`3px solid #2563EB`).
- Collapsed view lists: "EMIs from ₹1,249/mo | No Cost EMI available on 8 banks".
- Expanded view reveals a multi-column comparison table detailing down payment, tenure, and monthly charges.